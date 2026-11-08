# Application Global Variables
# This module serves as a way to share variables across different
# modules (global variables) and manage persistent add-in settings.

import json
import os
import re
from typing import Any, Dict

# Flag that indicates to run in Debug mode or not. When running in Debug mode
# more information is written to the Text Command window.
DEBUG = True

# Gets the name of the add-in from the name of the folder the py file is in.
ADDIN_NAME = os.path.basename(os.path.dirname(__file__))
COMPANY_NAME = 'ACME'

# Palettes
sample_palette_id = f'{COMPANY_NAME}_{ADDIN_NAME}_palette_id'

# Persistent settings file path
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'MultiProjectSettings.json')

# Structured settings sections in the exact order they appear in the add-in
SETTINGS_SECTIONS = {
    # Toolbar Panel Placement
    'Toolbar Panel Placement': {
        'is_promoted': True,
        'dropdown_position_id': 'ProjectIncludeDropDown',
        'dropdown_is_before': False,
        'promoted_position_id': '',
        'promoted_is_before': False,
    },
    # Command Dialog Defaults
    'Command Dialog Defaults': {
        'default_filter_mode': 'Line / Geometry',
    },
}

# Flattened default settings dictionary organized by category
DEFAULTS: Dict[str, Any] = {
    # Toolbar Panel Placement
    'is_promoted': True,
    'dropdown_position_id': 'ProjectIncludeDropDown',
    'dropdown_is_before': False,
    'promoted_position_id': '',
    'promoted_is_before': False,

    # Command Dialog Defaults
    'default_filter_mode': 'Line / Geometry',
}

# In-memory cache to avoid redundant disk reads
_cached_settings: Dict[str, Any] = {}


def _strip_json_comments(raw_text: str) -> str:
    """Strips // and /* */ comments outside of JSON strings for comment-tolerant loading."""
    pattern = r'("(?:\\.|[^"\\])*")|//[^\r\n]*|/\*[\s\S]*?\*/'
    return re.sub(pattern, lambda m: m.group(1) if m.group(1) else '', raw_text)


def load_settings() -> Dict[str, Any]:
    """Loads settings from disk with comment tolerance, falling back to DEFAULTS."""
    global _cached_settings
    if _cached_settings:
        return dict(_cached_settings)

    settings = dict(DEFAULTS)
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                raw = f.read()
            cleaned = _strip_json_comments(raw)
            loaded = json.loads(cleaned)
            if isinstance(loaded, dict):
                for key in DEFAULTS:
                    if key in loaded:
                        settings[key] = loaded[key]
        except Exception:
            # Repair file if corrupted
            save_settings(settings)
    else:
        save_settings(settings)

    _cached_settings = dict(settings)
    return settings


def save_settings(settings: Dict[str, Any]) -> None:
    """Serializes settings to disk preserving category comments and key order."""
    global _cached_settings
    merged = dict(DEFAULTS)
    if isinstance(settings, dict):
        for k, v in settings.items():
            if k in merged:
                merged[k] = v

    _cached_settings = dict(merged)

    lines = ['{']
    section_names = list(SETTINGS_SECTIONS.keys())
    all_keys = [k for sec in SETTINGS_SECTIONS.values() for k in sec.keys()]
    total_keys = len(all_keys)
    key_counter = 0

    for sec_idx, sec_name in enumerate(section_names):
        if sec_idx > 0:
            lines.append('')
        lines.append(f'    // {sec_name}')
        sec_keys = list(SETTINGS_SECTIONS[sec_name].keys())
        for key in sec_keys:
            key_counter += 1
            val_json = json.dumps(merged.get(key, DEFAULTS[key]))
            comma = ',' if key_counter < total_keys else ''
            lines.append(f'    "{key}": {val_json}{comma}')

    lines.append('}')
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')
    except Exception:
        pass
