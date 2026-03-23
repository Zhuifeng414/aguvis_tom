# AGUVIS UI Task Delivery

## Task

Build a Streamlit-based UI tool, based on `inference_test.ipynb`, that lets a user:

- Upload an image
- Edit the inference parameters
  - `title`
  - `instruction`
  - `mode`
  - `previous_actions`
  - `low_level_instruction`
- Run the AGUVIS model
- View the model output in the UI

The requested default example was:

```python
{
    "title": "Example 4: grounding mode",
    "instruction": "Tap the Notifications option.",
    "mode": "grounding",
    "previous_actions": None,
    "low_level_instruction": "Tap the Notifications option",
}
```

The code also needed to be stored in a new subfolder.

## Solution

The solution is implemented as a Streamlit app in `streamlit_ui/app.py`.

Key design choices:

- The app reuses the existing AGUVIS inference code from `src/aguvis/serve/cli.py`
- The model is loaded once per `(model_path, device)` combination using Streamlit resource caching
- The UI defaults match the notebook's Example 4 grounding case
- Users can either upload their own image or use the bundled sample image
- The app shows both a request preview and the final model output
- Coordinate-based action outputs are visualized as red markers on the image
- Hovering over the image shows live normalized `x` and `y` coordinates

This keeps the UI aligned with the notebook behavior instead of creating a separate inference implementation.

## Artifacts

Files created for this task:

- `streamlit_ui/app.py`
  - Main Streamlit application
- `streamlit_ui/visualization.py`
  - Action parsing and interactive image overlay rendering
- `streamlit_ui/README.md`
  - Short run instructions
- `streamlit_ui/DELIVERABLE.md`
  - This delivery document

Relevant existing file reused by the app:

- `src/aguvis/serve/cli.py`
  - Provides `load_pretrained_model`, `load_image`, and `generate_response`

Default example image used by the app:

- `src/aguvis/serve/examples/AndroidControl.png`

## How To Use The Product

Follow these steps from the repository root.

### 1. Install dependencies

Make sure your environment has the AGUVIS project dependencies installed.

If Streamlit is not installed yet, install it:

```bash
pip install streamlit
```

You also need the model runtime dependencies available in your environment, including `torch` and the AGUVIS project package.

### 2. Start the UI

Run:

```bash
streamlit run streamlit_ui/app.py
```

Streamlit will print a local URL in the terminal, usually something like:

```text
http://localhost:8501
```

Open that URL in your browser.

### 3. Configure the model

In the sidebar:

- Set `Model path`
  - Example: `xlangai/Aguvis-7B-720P`
  - Or a local checkpoint path
- Choose `Device`
  - `cuda` if a GPU is available
  - `cpu` otherwise
- Adjust `Temperature` if needed
- Adjust `Max new tokens` if needed

### 4. Provide the input image

In the main page:

- Click `Upload an image` and choose your image file
- Or leave it empty to use the bundled example image

The currently selected image will be shown in the UI.

### 5. Edit the task parameters

Fill in or modify:

- `Title`
- `Instruction`
- `Mode`
- `Previous actions`
  - One action per line
  - Or `None`
- `Low-level instruction`

The UI starts with the notebook Example 4 grounding defaults.

### 6. Review the request

Check the `Request Preview` panel on the right side.

This shows the exact payload that will be sent into AGUVIS inference.

### 7. Run inference

Click `Run inference`.

The app will:

- Load the model if it is not already cached
- Run AGUVIS inference on the current image and parameters
- Store the generated result in the current session

### 8. Read the output

Look at the `Model Output` panel.

The generated AGUVIS response will be displayed there.

### 9. Inspect the visualization

Look at the `Interactive Image` panel.

- If the action text contains coordinate pairs such as `(0.42, 0.68)`, the app draws red boxes on those positions
- If the action appears to describe a swipe and contains at least two coordinate pairs, the app also draws a connecting guide line
- When you move the mouse over the image, the UI shows the live normalized cursor position as `x` and `y`

### 10. Test a custom action manually

Use the `Action Visualization Source` text area.

- Paste or edit an action string such as `pyautogui.click(0.52, 0.31)`
- The image visualization updates using that action text
- This is useful even before running inference

## Notes

- The app is intended as a UI wrapper around the notebook inference workflow
- If `streamlit` or `torch` is missing, the app will not start until those dependencies are installed
- GPU inference is recommended for large vision-language checkpoints
