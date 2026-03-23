from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Literal, cast

import streamlit as st
import torch
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from aguvis.serve.cli import generate_response, load_image, load_pretrained_model
from visualization import render_action_visualization

DEFAULT_TITLE = "Example 4: grounding mode"
DEFAULT_INSTRUCTION = "Tap the Notifications option."
DEFAULT_MODE = "grounding"
DEFAULT_LOW_LEVEL_INSTRUCTION = "Tap the Notifications option"
DEFAULT_MODEL_PATH = "xlangai/Aguvis-7B-720P"
DEFAULT_IMAGE_PATH = REPO_ROOT / "src/aguvis/serve/examples/AndroidControl.png"
Mode = Literal["self-plan", "force-plan", "grounding"]


def available_devices() -> list[str]:
    if torch.cuda.is_available():
        return ["cuda", "cpu"]
    return ["cpu"]


def resolve_attn_implementation(device: str) -> str:
    if device == "cuda" and importlib.util.find_spec("flash_attn") is not None:
        return "flash_attention_2"
    return "eager"


def resolve_torch_dtype(device: str):
    if device == "cuda":
        return torch.bfloat16
    return None


@st.cache_resource(show_spinner=False)
def load_aguvis_model(model_path: str, device: str):
    model, processor, tokenizer = load_pretrained_model(
        model_path,
        attn_implementation=resolve_attn_implementation(device),
        torch_dtype=resolve_torch_dtype(device),
    )
    model.to(device)
    model.tie_weights()
    return model, processor, tokenizer


def parse_previous_actions(previous_actions_text: str) -> list[str] | None:
    stripped = previous_actions_text.strip()
    if not stripped or stripped.lower() == "none":
        return None
    return [line.strip() for line in stripped.splitlines() if line.strip()]


def load_selected_image(uploaded_file) -> Image.Image:
    if uploaded_file is not None:
        return Image.open(uploaded_file).convert("RGB")
    return load_image(str(DEFAULT_IMAGE_PATH))


def main():
    st.set_page_config(page_title="AGUVIS UI Tester", layout="wide")
    st.title("AGUVIS Streamlit UI")
    st.caption("Upload an image, edit the inference fields, run inference, and visualize coordinate-based actions.")
    st.session_state.setdefault("visualized_action_text", "")
    st.session_state.setdefault("pending_visualization_refresh", False)

    with st.sidebar:
        st.header("Model Settings")
        model_path = st.text_input("Model path", value=DEFAULT_MODEL_PATH)
        device = st.selectbox("Device", options=available_devices(), index=0)
        temperature = st.slider("Temperature", min_value=0.0, max_value=2.0, value=0.0, step=0.1)
        max_new_tokens = st.number_input("Max new tokens", min_value=1, max_value=4096, value=512, step=1)
        st.markdown(f"Default sample image: `{DEFAULT_IMAGE_PATH.relative_to(REPO_ROOT)}`")

    left_col, right_col = st.columns([1.1, 0.9], gap="large")

    with left_col:
        st.subheader("Inputs")
        uploaded_file = st.file_uploader(
            "Upload an image",
            type=["png", "jpg", "jpeg", "webp"],
            help="If no image is uploaded, the bundled Android example image is used.",
        )

        title = st.text_input("Title", value=DEFAULT_TITLE)
        instruction = st.text_area("Instruction", value=DEFAULT_INSTRUCTION, height=100)
        mode_options: list[Mode] = ["self-plan", "force-plan", "grounding"]
        mode = cast(
            Mode,
            st.selectbox(
                "Mode",
                options=mode_options,
                index=mode_options.index(DEFAULT_MODE),
            ),
        )
        previous_actions_text = st.text_area(
            "Previous actions",
            value="None",
            height=120,
            help="Enter one action per line, or leave as `None`.",
        )
        low_level_instruction = st.text_input("Low-level instruction", value=DEFAULT_LOW_LEVEL_INSTRUCTION)

        current_image = load_selected_image(uploaded_file)
        st.subheader("Interactive Image")
        st.caption("Red markers show parsed action coordinates. Hover to inspect live normalized x/y values.")
        action_text_for_visualization = st.session_state["visualized_action_text"]
        parsed_points = render_action_visualization(current_image, action_text_for_visualization)
        if parsed_points:
            st.caption(f"Visualized {len(parsed_points)} coordinate point(s) from the current action text.")
            st.code(str(parsed_points), language="python")
        elif action_text_for_visualization.strip():
            st.caption("No supported coordinate pairs were parsed from the current action text.")
            st.caption("Supported examples: `pyautogui.click(0.52, 0.31)` or `x=0.52, y=0.31`.")
        else:
            st.caption("No coordinate pairs detected in the current action text yet.")

        run_button = st.button("Run inference", type="primary", use_container_width=True)

    with right_col:
        st.subheader("Request Preview")
        previous_actions = parse_previous_actions(previous_actions_text)
        request_payload = {
            "title": title,
            "instruction": instruction,
            "mode": mode,
            "previous_actions": previous_actions,
            "low_level_instruction": low_level_instruction or None,
        }
        st.json(request_payload)

        if run_button:
            if not model_path.strip():
                st.error("Model path is required.")
            else:
                with st.spinner("Loading model and running inference..."):
                    model, processor, tokenizer = load_aguvis_model(model_path.strip(), device)
                    response = generate_response(
                        model=model,
                        processor=processor,
                        tokenizer=tokenizer,
                        image=current_image,
                        instruction=instruction,
                        previous_actions=previous_actions,
                        low_level_instruction=low_level_instruction or None,
                        mode=mode,
                        temperature=temperature,
                        max_new_tokens=int(max_new_tokens),
                    )
                st.session_state["last_response"] = response
                st.session_state["last_title"] = title
                st.session_state["visualized_action_text"] = response
                st.session_state["pending_visualization_refresh"] = True

        st.subheader("Model Output")
        if "last_response" in st.session_state:
            st.markdown(f"**{st.session_state.get('last_title', 'Latest run')}**")
            st.code(st.session_state["last_response"], language="text")
        else:
            st.info("Run inference to see the model output here.")

        st.subheader("Action Visualization Source")
        st.text_area(
            "Action text",
            key="visualized_action_text",
            height=140,
            help="Edit this text to test the red-box visualization. Coordinate pairs like `(0.52, 0.31)` are supported.",
        )

    if st.session_state.get("pending_visualization_refresh"):
        st.session_state["pending_visualization_refresh"] = False
        st.rerun()


if __name__ == "__main__":
    main()
