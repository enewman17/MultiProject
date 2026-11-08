---
description: Recursively finds and purges all __pycache__ directories and compiled Python bytecode files (.pyc, .pyo) across the entire repository.
---

### Workflow Rule: Repository Cache Cleanup

#### Trigger Parameters:
- **Event:** Text command processing.
- **Activation Keyword:** The user explicitly types `clean_cache` (case-insensitive, e.g., "clean_cache", "clean cache", "run clean_cache", "/clean_cache") inside the agent prompt chat box.

#### Agent Execution Pipeline:
1. Upon matching the activation keyword, the agent must immediately execute the cache cleanup script:
   ```bash
   python .vscode/clean_cache.py
   ```
2. While the script runs, reply to the user in chat acknowledging the start of the cleanup (e.g., "Cleaning all __pycache__ folders from repository...").

#### Terminal Logging and Output Controls:
- If the execution completes with exit status code `0`, reply directly in the chat panel with a successful summary: `[+] Repository Cache Cleaned Successfully.`
- If the exit status code is non-zero, surface the standard `traceback` runtime error stack inside a highlighted debug panel for troubleshooting.
