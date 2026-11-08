---
description: Automates the compilation, cleanup, and synchronization of Autodesk Fusion add-in development assets from the local IDE workspace directly into Fusion's native internal test directory.
---

### Workflow Rule: Autodesk Fusion Add-In Conversational Deployment

#### Trigger Parameters:
- **Event:** Text command processing.
- **Activation Keyword:** The user explicitly types `deploy` (case-insensitive, e.g., "deploy", "please deploy", "run deploy") inside the agent prompt chat box.

#### Agent Execution Pipeline:
1. Upon matching the activation keyword, the agent must immediately execute the background deployment script:
   ```bash
   python .vscode/deploy.py
   ```
2. While the script runs, reply to the user in chat acknowledging the start of the synchronization (e.g., "Deploying your add-in files to Fusion now...").

#### Terminal Logging and Output Controls:
- Clear the previous active deployment terminal log block right before executing a fresh synchronization.
- If the execution completes with exit status code `0`, reply directly in the chat panel with a successful summary: `[+] Add-In Synchronized Successfully.`
- If the exit status code is non-zero, surface the standard `traceback` runtime error stack inside a highlighted debug panel for troubleshooting.
