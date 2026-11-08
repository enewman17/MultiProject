---
description: Procedures for handling Fusion MCP connection loss, stopping retries, confirming crashes, and gathering/analyzing Autodesk crash logs.
---

# Handling Fusion MCP Connection Loss & Crash Diagnosis

When an MCP call to Autodesk Fusion 360 fails with a connection error (e.g., connection refused on port 27182, session lost, or broken pipe):

## 1. Immediate Halt
- **DO NOT** attempt to reconnect or poll the MCP in a loop.
- **DO NOT** launch background processes to ping or query the MCP port repeatedly.
- Stop immediately.

## 2. Stop and Confirm
- Ask the user if Autodesk Fusion 360 crashed or was closed.

## 3. Crash Log Gathering
If the program crashed, execute PowerShell queries to retrieve the latest crash logs:

```powershell
# 1. Check Autodesk Customer Error Report (CER) logs:
Get-ChildItem -Path "$env:LOCALAPPDATA\Autodesk\CER" -Recurse -Filter "*.log" | Sort-Object LastWriteTime -Descending | Select-Object -First 3

# 2. Check Fusion 360 Application and Platform logs:
Get-ChildItem -Path "$env:LOCALAPPDATA\Autodesk\Autodesk Fusion 360" -Recurse -Filter "AppLogFile*.log" | Sort-Object LastWriteTime -Descending | Select-Object -First 3

# 3. Check Neutron Platform logs:
Get-ChildItem -Path "$env:LOCALAPPDATA\Autodesk\Neutron Platform\logs" -Filter "AppLogFile*.log" | Sort-Object LastWriteTime -Descending | Select-Object -First 2
```

## 4. Root Cause Analysis
- Inspect the trailing lines and stack traces in the retrieved log files.
- Common failure modes triggered by commands run through the MCP:
  - **Concurrent Document/Thread Operations**: Modifying documents or switching active documents (`doc.activate()`) while background threads or commands are active.
  - **Modal State Violation**: Attempting to execute non-read-only scripts while a dialog or command definition is active.
  - **Dangling C++ Reference Handles**: Manipulating B-Rep bodies, faces, or occurrences without properly releasing native object handles.
  - **Memory Access Violation**: Direct geometry boolean operations with invalid geometry parameters.

## 5. Remediation & Code Guarding
- Identify the exact command or script that triggered the crash.
- Implement defensive guards, error checking, and object validation before executing similar operations.
