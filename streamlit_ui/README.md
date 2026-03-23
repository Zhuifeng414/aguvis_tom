# AGUVIS Streamlit UI

This folder contains a small Streamlit app that wraps the notebook inference flow from `inference_test.ipynb`.

## Run

Install Streamlit if it is not already available:

```bash
pip install streamlit
```

Start the app from the repository root:

```bash
streamlit run streamlit_ui/app.py
```

## What it does

- Uploads an image, or falls back to `src/aguvis/serve/examples/AndroidControl.png`
- Exposes the notebook-style fields `title`, `instruction`, `mode`, `previous_actions`, and `low_level_instruction`
- Loads the AGUVIS model once per `(model_path, device)` combination with Streamlit caching
- Displays the generated model output in the UI
- Visualizes coordinate-based actions with red markers on top of the image
- Shows live normalized mouse coordinates while hovering over the image
