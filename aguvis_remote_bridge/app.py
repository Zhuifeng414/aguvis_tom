from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Literal, cast

import requests
import streamlit as st
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from aguvis_remote_bridge.common import (
    DEFAULT_IMAGE_PATH,
    DEFAULT_LOW_LEVEL_INSTRUCTION,
    DEFAULT_MODE,
    DEFAULT_SERVER_URL,
    DEFAULT_TITLE,
    DEFAULT_INSTRUCTION,
    LATEST_RESULT_PATH,
    LOCAL_CAPTURE_DIR,
    SETTINGS_PATH,
    STREAMLIT_UI_ROOT,
    atomic_write_json,
    default_settings,
    ensure_local_state_dirs,
    latest_file_token,
    load_json,
    parse_previous_actions_text,
    previous_actions_to_text,
)

if str(STREAMLIT_UI_ROOT) not in sys.path:
    sys.path.insert(0, str(STREAMLIT_UI_ROOT))

from visualization import render_action_visualization

Mode = Literal["self-plan", "force-plan", "grounding"]
RESULT_WATCH_INTERVAL = "2s"


def normalize_health_url(server_url: str) -> str:
    cleaned = server_url.rstrip("/")
    if cleaned.endswith("/infer"):
        cleaned = cleaned[: -len("/infer")]
    return f"{cleaned}/health"


def load_latest_result() -> dict[str, Any] | None:
    return load_json(LATEST_RESULT_PATH)


def load_display_image(latest_result: dict[str, Any] | None) -> tuple[Image.Image, str]:
    if latest_result:
        image_path_value = latest_result.get("image_path")
        if isinstance(image_path_value, str) and image_path_value:
            image_path = Path(image_path_value)
            if image_path.exists():
                return Image.open(image_path).convert("RGB"), f"latest local screenshot: {image_path}"

    return Image.open(DEFAULT_IMAGE_PATH).convert("RGB"), f"default sample: {DEFAULT_IMAGE_PATH}"


@st.cache_data(show_spinner=False, ttl=5)
def fetch_server_health(server_url: str) -> dict[str, Any]:
    response = requests.get(normalize_health_url(server_url), timeout=3)
    response.raise_for_status()
    return response.json()


@st.fragment(run_every=RESULT_WATCH_INTERVAL)
def watch_latest_result() -> None:
    current_token = latest_file_token(LATEST_RESULT_PATH)
    previous_token = st.session_state.get("latest_result_token")
    if previous_token is None:
        st.session_state["latest_result_token"] = current_token
    elif current_token != previous_token:
        st.session_state["latest_result_token"] = current_token
        st.rerun()

    latest_result = load_latest_result()
    if latest_result is None:
        st.caption(f"Watching `{LATEST_RESULT_PATH}`. No screenshots processed yet.")
        return

    status = latest_result.get("status", "unknown")
    captured_at = latest_result.get("captured_at", "unknown time")
    st.caption(f"Latest local result status: `{status}` at `{captured_at}`")


def main() -> None:
    ensure_local_state_dirs()
    st.set_page_config(page_title="AGUVIS Remote Bridge UI", layout="wide")
    st.title("AGUVIS Remote Bridge")
    st.caption(
        "Run AGUVIS inference on the Linux server, keep this Streamlit app on the local computer, "
        "and refresh the latest screenshot and response whenever the hotkey client captures `kk`."
    )

    saved_settings = default_settings()
    saved_settings.update(load_json(SETTINGS_PATH) or {})
    watch_latest_result()

    st.session_state.setdefault("visualized_action_text", "")
    st.session_state.setdefault("visualized_result_token", "")

    with st.sidebar:
        st.header("Remote Settings")
        server_url = st.text_input("Server URL", value=str(saved_settings.get("server_url", DEFAULT_SERVER_URL)))
        title = st.text_input("Title", value=str(saved_settings.get("title", DEFAULT_TITLE)))
        instruction = st.text_area(
            "Instruction",
            value=str(saved_settings.get("instruction", DEFAULT_INSTRUCTION)),
            height=100,
        )
        mode_options: list[Mode] = ["self-plan", "force-plan", "grounding"]
        configured_mode = str(saved_settings.get("mode", DEFAULT_MODE))
        mode = cast(
            Mode,
            st.selectbox(
                "Mode",
                options=mode_options,
                index=mode_options.index(configured_mode if configured_mode in mode_options else DEFAULT_MODE),
            ),
        )
        previous_actions_text = st.text_area(
            "Previous actions",
            value=previous_actions_to_text(saved_settings.get("previous_actions")),
            height=120,
            help="Enter one action per line, or leave as `None`.",
        )
        low_level_instruction = st.text_input(
            "Low-level instruction",
            value=str(saved_settings.get("low_level_instruction", DEFAULT_LOW_LEVEL_INSTRUCTION)),
        )
        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=2.0,
            value=float(saved_settings.get("temperature", 0.0)),
            step=0.1,
        )
        max_new_tokens = st.number_input(
            "Max new tokens",
            min_value=1,
            max_value=4096,
            value=int(saved_settings.get("max_new_tokens", 512)),
            step=1,
        )
        st.caption(f"Hotkey screenshots are stored in `{LOCAL_CAPTURE_DIR}`.")
        st.caption(f"Live settings are written to `{SETTINGS_PATH}` for the hotkey client.")

    current_settings = {
        "server_url": server_url.strip() or DEFAULT_SERVER_URL,
        "title": title,
        "instruction": instruction,
        "mode": mode,
        "previous_actions": parse_previous_actions_text(previous_actions_text),
        "low_level_instruction": low_level_instruction or None,
        "temperature": float(temperature),
        "max_new_tokens": int(max_new_tokens),
    }
    atomic_write_json(SETTINGS_PATH, current_settings)

    latest_result = load_latest_result()
    current_image, image_source_label = load_display_image(latest_result)
    current_result_token = latest_file_token(LATEST_RESULT_PATH)
    latest_response_text = ""
    if latest_result and isinstance(latest_result.get("response_text"), str):
        latest_response_text = latest_result["response_text"]

    if st.session_state["visualized_result_token"] != current_result_token:
        st.session_state["visualized_result_token"] = current_result_token
        st.session_state["visualized_action_text"] = latest_response_text

    left_col, right_col = st.columns([1.1, 0.9], gap="large")

    with left_col:
        st.subheader("Latest Screenshot")
        st.caption(f"Current image source: `{image_source_label}`")
        parsed_points = render_action_visualization(current_image, st.session_state["visualized_action_text"])
        if parsed_points:
            st.caption(f"Visualized {len(parsed_points)} coordinate point(s) from the latest response text.")
            st.code(str(parsed_points), language="python")
        elif st.session_state["visualized_action_text"].strip():
            st.caption("No supported coordinate pairs were parsed from the current action text.")
        else:
            st.caption("No model output has been received yet.")

    with right_col:
        st.subheader("Backend Status")
        try:
            health_payload = fetch_server_health(current_settings["server_url"])
            st.success(
                f"Connected to backend on `{health_payload.get('device', 'unknown')}` with "
                f"`{health_payload.get('model_path', 'unknown model')}`."
            )
            st.json(health_payload)
        except Exception as exc:
            st.error(f"Backend health check failed: {exc}")

        st.subheader("Current Request Settings")
        st.json(current_settings)

        st.subheader("Backend Result")
        if latest_result is None:
            st.info("Run the local hotkey client and type `kk` to capture a screenshot and request inference.")
        elif latest_result.get("status") == "error":
            st.error(str(latest_result.get("error", "Unknown error")))
        else:
            st.code(latest_response_text, language="text")
            if isinstance(latest_result.get("server_payload"), dict):
                st.caption(
                    f"Server runtime: `{latest_result['server_payload'].get('duration_seconds', 'unknown')}` seconds"
                )

        st.subheader("Action Visualization Source")
        st.text_area(
            "Action text",
            key="visualized_action_text",
            height=140,
            help="Edit this text to test the red-box visualization against the latest screenshot.",
        )


if __name__ == "__main__":
    main()
