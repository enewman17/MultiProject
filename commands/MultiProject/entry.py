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

# Specify that the command will be promoted to the panel by default
IS_PROMOTED = True

# Target toolbar panel and default placement
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

        # Clean up any existing instance to support seamless hot-reloading,
        # saving its position first if it already exists in the panel.
        stop()

        # Load persistent user settings (including saved panel placement)
        settings = config.load_settings()
        is_promoted = bool(settings.get('is_promoted', IS_PROMOTED))
        drop_pos_id = str(settings.get('dropdown_position_id', COMMAND_BESIDE_ID) or '')
        drop_is_before = bool(settings.get('dropdown_is_before', False))
        prom_pos_id = str(settings.get('promoted_position_id', '') or '')
        prom_is_before = bool(settings.get('promoted_is_before', False))

        # Create the command definition
        cmd_def = ui.commandDefinitions.addButtonDefinition(
            CMD_ID,
            CMD_NAME,
            CMD_DESCRIPTION,
            ICON_FOLDER
        )

        # Define an event handler for the command created event
        futil.add_handler(cmd_def.commandCreated, command_created)

        # Listen to command termination so any user drag/reorder of the button in the panel is saved
        futil.add_handler(ui.commandTerminated, on_ui_command_terminated)

        # Add button to the Sketch -> Create panel at its saved position
        panel = ui.allToolbarPanels.itemById(PANEL_ID)
        if panel:
            if drop_pos_id and panel.controls.itemById(drop_pos_id):
                control = panel.controls.addCommand(cmd_def, drop_pos_id, drop_is_before)
            elif panel.controls.itemById(COMMAND_BESIDE_ID):
                control = panel.controls.addCommand(cmd_def, COMMAND_BESIDE_ID, False)
            else:
                control = panel.controls.addCommand(cmd_def)

            if is_promoted:
                promoted_ok = False
                if prom_pos_id:
                    try:
                        promoted_ok = control.promote(True, prom_pos_id, prom_is_before)
                    except:
                        promoted_ok = False
                if not promoted_ok:
                    control.isPromoted = True
                    control.isPromotedByDefault = True
            else:
                control.isPromoted = False
                control.isPromotedByDefault = False

    except:
        futil.handle_error('start')


def stop():
    """Executed when add-in is stopped."""
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface

        panel = ui.allToolbarPanels.itemById(PANEL_ID)
        if panel:
            # Capture and save the user's current panel ordering before deleting the control
            active_ctrl = panel.controls.itemById(CMD_ID)
            if active_ctrl:
                _capture_panel_position(panel, adsk.core.CommandControl.cast(active_ctrl))

            # Clean up button control from panel
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


def _capture_panel_position(panel: adsk.core.ToolbarPanel, control: adsk.core.CommandControl):
    """Captures and persists the current ordering and promotion state of the button in the panel."""
    try:
        if not panel or not control or not control.isValid:
            return

        settings = config.load_settings()
        changed = False
        ignored_ids = {CMD_ID, 'MultiProjectCmd'}

        # 1. Promotion state
        is_promoted = bool(control.isPromoted)
        if settings.get('is_promoted') != is_promoted:
            settings['is_promoted'] = is_promoted
            changed = True

        # 2. Relative position inside panel.controls (dropdown menu order)
        controls = panel.controls
        ctrl_idx = -1
        for i in range(controls.count):
            item = controls.item(i)
            if item and item.id == control.id:
                ctrl_idx = i
                break

        if ctrl_idx >= 0:
            drop_pos_id = ''
            drop_is_before = False
            if ctrl_idx > 0:
                for j in range(ctrl_idx - 1, -1, -1):
                    prev_ctrl = controls.item(j)
                    if prev_ctrl and prev_ctrl.id and prev_ctrl.id not in ignored_ids:
                        drop_pos_id = prev_ctrl.id
                        drop_is_before = False
                        break
            if not drop_pos_id and controls.count > 1:
                for j in range(ctrl_idx + 1, controls.count):
                    next_ctrl = controls.item(j)
                    if next_ctrl and next_ctrl.id and next_ctrl.id not in ignored_ids:
                        drop_pos_id = next_ctrl.id
                        drop_is_before = True
                        break

            if drop_pos_id:
                if (settings.get('dropdown_position_id') != drop_pos_id or
                        settings.get('dropdown_is_before') != drop_is_before):
                    settings['dropdown_position_id'] = drop_pos_id
                    settings['dropdown_is_before'] = drop_is_before
                    changed = True

        # 3. Relative position inside panel.promotedControls (ribbon toolbar order)
        if is_promoted:
            prom_controls = panel.promotedControls
            prom_idx = -1
            for i in range(prom_controls.count):
                item = prom_controls.item(i)
                if item and item.id == control.id:
                    prom_idx = i
                    break

            if prom_idx >= 0:
                prom_pos_id = ''
                prom_is_before = False
                if prom_idx > 0:
                    for j in range(prom_idx - 1, -1, -1):
                        prev_prom = prom_controls.item(j)
                        if prev_prom and prev_prom.id and prev_prom.id not in ignored_ids:
                            prom_pos_id = prev_prom.id
                            prom_is_before = False
                            break
                if not prom_pos_id and prom_controls.count > 1:
                    for j in range(prom_idx + 1, prom_controls.count):
                        next_prom = prom_controls.item(j)
                        if next_prom and next_prom.id and next_prom.id not in ignored_ids:
                            prom_pos_id = next_prom.id
                            prom_is_before = True
                            break

                if prom_pos_id:
                    if (settings.get('promoted_position_id') != prom_pos_id or
                            settings.get('promoted_is_before') != prom_is_before):
                        settings['promoted_position_id'] = prom_pos_id
                        settings['promoted_is_before'] = prom_is_before
                        changed = True

        if changed:
            config.save_settings(settings)
            futil.log(
                f'{CMD_NAME}: Saved panel placement '
                f'(promoted={is_promoted}, '
                f'promoted_beside={settings.get("promoted_position_id")} [before={settings.get("promoted_is_before")}], '
                f'dropdown_beside={settings.get("dropdown_position_id")} [before={settings.get("dropdown_is_before")}])'
            )

    except:
        futil.handle_error('_capture_panel_position')


def _sync_panel_position():
    """Helper to inspect SketchCreatePanel and persist current button ordering."""
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        if not ui:
            return
        panel = ui.allToolbarPanels.itemById(PANEL_ID)
        if panel:
            ctrl = panel.controls.itemById(CMD_ID)
            if ctrl:
                _capture_panel_position(panel, adsk.core.CommandControl.cast(ctrl))
    except:
        pass


def on_ui_command_terminated(args: adsk.core.ApplicationCommandEventArgs):
    """Automatically saves panel position whenever commands finish in the UI."""
    _sync_panel_position()


def command_created(args: adsk.core.CommandCreatedEventArgs):
    """Called when user clicks the Multi-Project button."""
    try:
        futil.log(f'{CMD_NAME} Command Created Event')

        # Save panel position if the user moved the button prior to clicking it
        _sync_panel_position()

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
        settings = config.load_settings()
        default_mode = settings.get('default_filter_mode', FILTER_MODE_GEOMETRY)
        is_body_default = (default_mode == FILTER_MODE_BODY)

        # Row 1 (Top Row): Select Objects selection input
        sel_input = inputs.addSelectionInput(
            'selectionInput',
            'Select Objects',
            'Window select edges, faces, vertices, or sketch curves to project'
        )

        # Row 2: Selection Filter button row (Line / Geometry vs Body / Component)
        filter_row = inputs.addButtonRowCommandInput('filterRow', 'Selection Filter', False)
        filter_row.listItems.add(FILTER_MODE_GEOMETRY, not is_body_default, GEOMETRY_ICON_FOLDER)
        filter_row.listItems.add(FILTER_MODE_BODY, is_body_default, BODY_ICON_FOLDER)
        filter_row.tooltip = 'Switch between Line/Geometry and Body/Component selection modes.'

        # Apply initial selection filters matching active button row item
        if is_body_default:
            _apply_body_filters(sel_input)
        else:
            _apply_geometry_filters(sel_input)

        # Limits from 1 to 0 (infinite) enables window / crossing selection box
        sel_input.setSelectionLimits(1, 0)

        # Row 3: Link Projections checkbox (for Parametric modeling)
        design = adsk.fusion.Design.cast(app.activeProduct)
        is_parametric = design and (design.designType == adsk.fusion.DesignTypes.ParametricDesignType)

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

        # Ensure the top Select Objects input has active focus immediately
        sel_input.hasFocus = True

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
                mode_name = FILTER_MODE_BODY
            else:
                _apply_geometry_filters(sel_input)
                mode_name = FILTER_MODE_GEOMETRY

            # Keep focus on the Select Objects input on the top row
            sel_input.hasFocus = True

            # Persist preferred filter mode
            settings = config.load_settings()
            if settings.get('default_filter_mode') != mode_name:
                settings['default_filter_mode'] = mode_name
                config.save_settings(settings)

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
    """Cleans up local handlers and syncs panel order when the command dialog terminates."""
    try:
        futil.log(f'{CMD_NAME} Command Destroy Event')
        _sync_panel_position()
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
