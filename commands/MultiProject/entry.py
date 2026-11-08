import os
from typing import List

import adsk.core
import adsk.fusion

from ... import config
from ...lib import fusionAddInUtils as futil

# Command identity information
CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_MultiProject'
CMD_NAME = 'Multi-Project'
CMD_DESCRIPTION = 'Project multiple objects into the active sketch using window selection.'

# Specify that the command will be promoted to the panel
IS_PROMOTED = True

# Target toolbar panel and placement
PANEL_ID = 'SketchCreatePanel'
COMMAND_BESIDE_ID = 'ProjectIncludeDropDown'

# Resource locations for command and button row icons
ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', '')
GEOMETRY_ICON_FOLDER = os.path.join(ICON_FOLDER, 'geometry_filter', '')
BODY_ICON_FOLDER = os.path.join(ICON_FOLDER, 'body_filter', '')

# Filter mode constants
FILTER_MODE_GEOMETRY = 'Line / Geometry'
FILTER_MODE_BODY = 'Body / Component'

# Local list of event handlers used to maintain reference during command lifetime
local_handlers = []


def start():
    """Executed when add-in is started."""
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface

        # Clean up any existing instance to support seamless hot-reloading
        stop()

        # Create the command definition
        cmd_def = ui.commandDefinitions.addButtonDefinition(
            CMD_ID,
            CMD_NAME,
            CMD_DESCRIPTION,
            ICON_FOLDER
        )

        # Define an event handler for the command created event
        futil.add_handler(cmd_def.commandCreated, command_created)

        # Add button to the Sketch -> Create panel
        panel = ui.allToolbarPanels.itemById(PANEL_ID)
        if panel:
            beside_control = panel.controls.itemById(COMMAND_BESIDE_ID)
            if beside_control:
                control = panel.controls.addCommand(cmd_def, COMMAND_BESIDE_ID, False)
            else:
                control = panel.controls.addCommand(cmd_def)
            control.isPromoted = IS_PROMOTED
            control.isPromotedByDefault = IS_PROMOTED

    except:
        futil.handle_error('start')


def stop():
    """Executed when add-in is stopped."""
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface

        # Clean up button control from panel
        panel = ui.allToolbarPanels.itemById(PANEL_ID)
        if panel:
            for cid in (CMD_ID, 'MultiProjectCmd'):
                control = panel.controls.itemById(cid)
                if control:
                    control.deleteMe()

        # Clean up command definition
        for cid in (CMD_ID, 'MultiProjectCmd'):
            cmd_def = ui.commandDefinitions.itemById(cid)
            if cmd_def:
                cmd_def.deleteMe()

    except:
        futil.handle_error('stop')


def command_created(args: adsk.core.CommandCreatedEventArgs):
    """Called when user clicks the Multi-Project button."""
    try:
        futil.log(f'{CMD_NAME} Command Created Event')

        app = adsk.core.Application.get()
        ui = app.userInterface

        # Verify an active sketch is being edited
        sketch = adsk.fusion.Sketch.cast(app.activeEditObject)
        if not sketch:
            ui.messageBox('You must have an active sketch open to use Multi-Project.', CMD_NAME)
            return

        cmd = args.command

        # Connect command lifecycle event handlers
        futil.add_handler(cmd.execute, command_execute, local_handlers=local_handlers)
        futil.add_handler(cmd.inputChanged, command_input_changed, local_handlers=local_handlers)
        futil.add_handler(cmd.validateInputs, command_validate_inputs, local_handlers=local_handlers)
        futil.add_handler(cmd.destroy, command_destroy, local_handlers=local_handlers)

        inputs = cmd.commandInputs

        # Button Row Input for selecting Filter Mode
        filter_row = inputs.addButtonRowCommandInput('filterRow', 'Selection Filter', False)
        filter_row.listItems.add(FILTER_MODE_GEOMETRY, True, GEOMETRY_ICON_FOLDER)
        filter_row.listItems.add(FILTER_MODE_BODY, False, BODY_ICON_FOLDER)
        filter_row.tooltip = 'Switch between Line/Geometry and Body/Component selection modes.'

        # Create selection input
        sel_input = inputs.addSelectionInput(
            'selectionInput',
            'Select Objects',
            'Window select edges, faces, vertices, or sketch curves to project'
        )

        # Default filters: Line / Geometry mode
        _apply_geometry_filters(sel_input)

        # Limits from 1 to 0 (infinite) enables window / crossing selection box
        sel_input.setSelectionLimits(1, 0)

        # Detect Direct Modeling vs Parametric Modeling workflow
        design = adsk.fusion.Design.cast(app.activeProduct)
        is_parametric = design and (design.designType == adsk.fusion.DesignTypes.ParametricDesignType)

        # Add link option for Parametric modeling
        link_input = inputs.addBoolValueInput(
            'link_input',
            'Link Projections',
            True,
            '',
            bool(is_parametric)
        )
        if not is_parametric:
            link_input.isEnabled = False
            link_input.value = False
            link_input.tooltip = 'Projection linking is disabled in Direct Modeling (no timeline history).'
        else:
            link_input.tooltip = 'Maintain parametric associative link to source geometry.'

    except:
        futil.handle_error('command_created')


def command_input_changed(args: adsk.core.InputChangedEventArgs):
    """Handles real-time switching between Line/Geometry and Body/Component filter modes."""
    try:
        changed_input = args.input
        if changed_input and changed_input.id == 'filterRow':
            btn_row = adsk.core.ButtonRowCommandInput.cast(changed_input)
            inputs = args.inputs
            sel_input = adsk.core.SelectionCommandInput.cast(inputs.itemById('selectionInput'))
            if not sel_input or not btn_row:
                return

            # Clear previous selection filters and clear existing selections for clean switch
            sel_input.clearSelectionFilter()
            sel_input.clearSelection()

            selected_item = btn_row.selectedItem
            if selected_item and selected_item.name == FILTER_MODE_BODY:
                _apply_body_filters(sel_input)
            else:
                _apply_geometry_filters(sel_input)

    except:
        futil.handle_error('command_input_changed')


def _apply_geometry_filters(sel_input: adsk.core.SelectionCommandInput):
    """Sets selection filters for Line / Geometry mode."""
    sel_input.addSelectionFilter('Edges')
    sel_input.addSelectionFilter('Faces')
    sel_input.addSelectionFilter('Vertices')
    sel_input.addSelectionFilter('SketchCurves')
    sel_input.addSelectionFilter('SketchPoints')
    sel_input.tooltip = 'Window select edges, faces, vertices, or sketch curves to project.'


def _apply_body_filters(sel_input: adsk.core.SelectionCommandInput):
    """Sets selection filters for Body / Component mode."""
    sel_input.addSelectionFilter('SolidBodies')
    sel_input.addSelectionFilter('SurfaceBodies')
    sel_input.addSelectionFilter('Occurrences')
    sel_input.tooltip = 'Window select solid bodies, surface bodies, or components to project.'


def command_validate_inputs(args: adsk.core.ValidateInputsEventArgs):
    """Enables the OK button only when at least one object has been selected."""
    try:
        inputs = args.inputs
        sel_input: adsk.core.SelectionCommandInput = inputs.itemById('selectionInput')
        if sel_input and sel_input.selectionCount > 0:
            args.areInputsValid = True
        else:
            args.areInputsValid = False
    except:
        futil.handle_error('command_validate_inputs')


def command_destroy(args: adsk.core.CommandEventArgs):
    """Cleans up local handlers when the command dialog terminates."""
    try:
        futil.log(f'{CMD_NAME} Command Destroy Event')
        global local_handlers
        local_handlers = []
    except:
        futil.handle_error('command_destroy')


def command_execute(args: adsk.core.CommandEventArgs):
    """Executes the projection operation when user clicks OK."""
    try:
        futil.log(f'{CMD_NAME} Command Execute Event')

        app = adsk.core.Application.get()
        ui = app.userInterface

        sketch = adsk.fusion.Sketch.cast(app.activeEditObject)
        if not sketch:
            ui.messageBox('You must have an active sketch open to use Multi-Project.', CMD_NAME)
            return

        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            return

        inputs = args.command.commandInputs
        sel_input: adsk.core.SelectionCommandInput = inputs.itemById('selectionInput')
        if not sel_input or sel_input.selectionCount == 0:
            return

        # Gather all selected entities into a list first before modifying the sketch.
        entities_to_project = []
        for i in range(sel_input.selectionCount):
            sel = sel_input.selection(i)
            if not sel or not sel.entity:
                continue
            entity = sel.entity

            # Prevent projecting entities that belong to the active sketch itself
            if hasattr(entity, 'parentSketch') and entity.parentSketch == sketch:
                continue

            if entity not in entities_to_project:
                entities_to_project.append(entity)

        # Defensively unpack Occurrences/Components into BRepBodies so we project valid
        # geometry rather than raw Occurrence pointers which cause native C++ access violations
        unpacked_entities = _extract_projectable_entities(entities_to_project)

        if not unpacked_entities:
            ui.messageBox('No valid external entities or bodies found to project.', CMD_NAME)
            return

        is_direct = (design.designType == adsk.fusion.DesignTypes.DirectDesignType)

        if is_direct:
            projected_count = _project_direct_modeling(sketch, unpacked_entities)
        else:
            link_input: adsk.core.BoolValueCommandInput = inputs.itemById('link_input')
            is_linked = link_input.value if link_input else True
            projected_count = _project_parametric_modeling(sketch, unpacked_entities, is_linked)

        futil.log(f'{CMD_NAME}: Successfully projected {projected_count} of {len(unpacked_entities)} entities.')

        if projected_count == 0:
            ui.messageBox(
                'None of the selected entities could be projected onto the active sketch plane.\n'
                'Please verify the selected entities are valid for projection.',
                CMD_NAME
            )

    except:
        futil.handle_error('command_execute')


def _extract_projectable_entities(entities: list) -> list:
    """Unpack occurrences/components into constituent visible BRepBodies and deduplicate."""
    extracted = []

    def process_occurrence(occ: adsk.fusion.Occurrence):
        try:
            # First extract bodies directly from occurrence proxy context
            bodies = occ.bRepBodies
            if bodies.count == 0 and hasattr(occ, 'component') and occ.component:
                bodies = occ.component.bRepBodies

            for i in range(bodies.count):
                body = bodies.item(i)
                if body and body.isValid and body not in extracted:
                    extracted.append(body)

            # Recursively unpack any child occurrences / sub-components
            if hasattr(occ, 'childOccurrences'):
                for j in range(occ.childOccurrences.count):
                    child = occ.childOccurrences.item(j)
                    if child and child.isValid:
                        process_occurrence(child)
        except:
            pass

    for ent in entities:
        if isinstance(ent, adsk.fusion.Occurrence):
            process_occurrence(ent)
        elif isinstance(ent, adsk.fusion.BRepBody):
            if ent.isValid and ent not in extracted:
                extracted.append(ent)
        else:
            if ent not in extracted:
                extracted.append(ent)

    return extracted


def _project_direct_modeling(sketch: adsk.fusion.Sketch, entities: List[adsk.core.Base]) -> int:
    """Execute projection workflow specifically for Direct Modeling (no history timeline)."""
    success_count = 0
    was_deferred = sketch.isComputeDeferred
    try:
        sketch.isComputeDeferred = True

        # In Direct Modeling, curves are unlinked to avoid orphaned parametric dependencies
        try:
            results = sketch.project2(entities, False)
            if results:
                return len(entities)
        except:
            pass

        # Fallback to individual projection
        for entity in entities:
            try:
                sketch.project2([entity], False)
                success_count += 1
            except:
                try:
                    sketch.project(entity)
                    success_count += 1
                except:
                    pass
    finally:
        sketch.isComputeDeferred = was_deferred

    return success_count


def _project_parametric_modeling(sketch: adsk.fusion.Sketch, entities: List[adsk.core.Base], is_linked: bool) -> int:
    """Execute projection workflow specifically for Parametric Modeling (timeline enabled)."""
    success_count = 0
    was_deferred = sketch.isComputeDeferred
    try:
        sketch.isComputeDeferred = True

        # Attempt batch projection with specified link setting
        try:
            results = sketch.project2(entities, is_linked)
            if results:
                return len(entities)
        except:
            pass

        # Fallback to individual projection
        for entity in entities:
            try:
                sketch.project2([entity], is_linked)
                success_count += 1
            except:
                try:
                    sketch.project(entity)
                    success_count += 1
                except:
                    pass
    finally:
        sketch.isComputeDeferred = was_deferred

    return success_count
