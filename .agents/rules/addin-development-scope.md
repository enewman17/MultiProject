---
trigger: always_on
---

### Core Development Philosophy:
1. Strict Object-Oriented Architecture: Prioritize strong modular structures, separation of concerns, and distinct business logic. Avoid single-script files for complex features.
2. Defensive Memory Management: Autodesk Fusion's API interfaces with an underlying native C++ engine. You MUST track all registered UI elements, events, and custom data wrappers.
3. Clean UI Execution: All custom buttons, panels, and command dialogs must be initialized cleanly and completely purged upon termination.

### Modeling Paradigm & Architectural Constraints:
1. All functions Should work in both Parameteric Modeling and Direct Modeling Workflows: Design all add-in functions, automated geometry manipulations, and operations to target each mode individually with their own unique workflow. 
2. Direct Modeling Workarounds: Acknowledge that Direct Modeling omits the history timeline and parameters, which presents unique challenges (e.g., lack of feature history dependencies, disappearing parameter structures). Always construct robust B-Rep traversal and face-tracking routines to navigate these direct geometry manipulation hurdles natively.
3. Parametric Performance: Actively avoid designing logic that relies heavily on a lengthy Parametric timeline. Parametric history calculation chains scale slowly and are poorly suited for large-scale hybrid designs or programmatic tree re-organization within the Fusion browser. Implement clean, direct geometry transformations instead of generating deep feature-history dependency trees.
4. All commands in fusion add-ins must work in both direct modeling and parametric mode. Seperate solutions for each mode, they should have their own path for achieving the goal of the command. 
5. Use deferred compute where possible.  

### Third-Party Module & Dependency Guidelines:
1. Leverage Existing Libraries: Do not reinvent the wheel. Prioritize the use of established, robust third-party modules to execute functions rather than writing custom code for problems that are already solved.
2. Excel, Data, & Math Integration: Utilize industry-standard packages whenever handling complex math, analytics, or external spreadsheet data formats. Approved examples include:
   - Spreadsheet / XML parsing: openpyxl, xlrd, xlsxwriter, xlwt, et_xmlfile
   - Scientific computing & matrix manipulation: NumPy, SciPy
3. Explicit Directory Bundling: All external third-party modules must be stored locally inside the add-in's `lib\modules` folder. 
4. Automated Path Insertion: When generating script templates that rely on these libraries, always include a defensive, boilerplate header snippet at the top of the file to programmatically append this exact `lib\modules` path to `sys.path`. This ensures the embedded Fusion Python interpreter locates them flawlessly without user intervention.

### Coding & API Standards:
- Always reference the official Fusion API object hierarchy (`adsk.core`, `adsk.fusion`).
- NEVER wrap global-level objects directly without a mechanism to release their reference pointer handles.
- Use explicit Type Hinting wherever possible to aid compilation and IDE intelligence.
- Implement robust exception handling inside all command hooks to prevent crashing the host Fusion application thread.
- Always check if a UI element (Panel, CommandDefinition, Control) already exists before creating it, ensuring seamless hot-reloading during iterative testing.
- Prioitize the use of modules for repeat operations that span across multiple commands.

### Settings & Configuration Organization:
- ALWAYS keep configuration settings in `config.py` (`DEFAULTS`, `SETTINGS_SECTIONS`) and `FrameGenSettings.json` organized strictly by category and in the exact order they appear in the add-in commands.
- Break each section with a comment indicating which category the values belong to.
- Ensure comment-tolerant loading and structured serialization are maintained so category comments and order are never overwritten or lost during save/repair operations.

### USE THE AUTODESK FUSION MCP:
- Always utilize Fusion's mcp to test features and debug problems before reaching a finial solution.
- Check, double check, tripple check, use multiple agents if necessary to make sure the command functions correctly.