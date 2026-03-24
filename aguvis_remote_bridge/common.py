from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

BRIDGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = BRIDGE_ROOT.parent
SRC_ROOT = REPO_ROOT / "src"
STREAMLIT_UI_ROOT = REPO_ROOT / "streamlit_ui"

DEFAULT_TITLE = "Example 4: grounding mode"
DEFAULT_INSTRUCTION = "Tap the Notifications option."
DEFAULT_MODE = "grounding"
DEFAULT_LOW_LEVEL_INSTRUCTION = "Tap the Notifications option"
DEFAULT_TRIGGER = "kk"
DEFAULT_SERVER_URL = "http://127.0.0.1:8766"
DEFAULT_IMAGE_PATH = REPO_ROOT / "src/aguvis/serve/examples/AndroidControl.png"

LOCAL_STATE_DIR = BRIDGE_ROOT / "local_state"
LOCAL_CAPTURE_DIR = LOCAL_STATE_DIR / "captures"
LOCAL_RESULTS_DIR = LOCAL_STATE_DIR / "results"
SETTINGS_PATH = LOCAL_STATE_DIR / "current_settings.json"
LATEST_RESULT_PATH = LOCAL_STATE_DIR / "latest_result.json"

SERVER_STATE_DIR = BRIDGE_ROOT / "server_state"
SERVER_UPLOAD_DIR = SERVER_STATE_DIR / "uploads"
SERVER_RESULT_DIR = SERVER_STATE_DIR / "results"
SERVER_LATEST_RESULT_PATH = SERVER_STATE_DIR / "latest_result.json"


def ensure_local_state_dirs() -> None:
    for path in (LOCAL_STATE_DIR, LOCAL_CAPTURE_DIR, LOCAL_RESULTS_DIR):
        path.mkdir(parents=True, exist_ok=True)


def ensure_server_state_dirs() -> None:
    for path in (SERVER_STATE_DIR, SERVER_UPLOAD_DIR, SERVER_RESULT_DIR):
        path.mkdir(parents=True, exist_ok=True)


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(f"{path.suffix}.tmp")
    temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temp_path, path)


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def latest_file_token(path: Path) -> str:
    if not path.exists():
        return "missing"
    stat_result = path.stat()
    return f"{path.name}:{stat_result.st_mtime_ns}:{stat_result.st_size}"


def parse_previous_actions_text(previous_actions_text: str) -> list[str] | None:
    stripped = previous_actions_text.strip()
    if not stripped or stripped.lower() == "none":
        return None
    return [line.strip() for line in stripped.splitlines() if line.strip()]


def previous_actions_to_text(previous_actions: list[str] | None) -> str:
    if not previous_actions:
        return "None"
    return "\n".join(previous_actions)


def encode_image_file(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def default_settings() -> dict[str, Any]:
    return {
        "server_url": DEFAULT_SERVER_URL,
        "title": DEFAULT_TITLE,
        "instruction": DEFAULT_INSTRUCTION,
        "mode": DEFAULT_MODE,
        "previous_actions": None,
        "low_level_instruction": DEFAULT_LOW_LEVEL_INSTRUCTION,
        "temperature": 0.0,
        "max_new_tokens": 512,
    }
