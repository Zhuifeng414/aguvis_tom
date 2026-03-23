# AGUVIS Hotkey Screenshot Bridge

This folder adds a separate workflow on top of the existing `streamlit_ui/` app without modifying it.

## What it does

1. `upload_server.py` runs on your server and accepts screenshot uploads at `/upload`.
2. `local_hotkey_client.py` runs on your local computer, watches for the `kk` key sequence, saves a local `.png`, and uploads it to the server.
3. `app.py` is a Streamlit variant of the existing UI that automatically uses the newest uploaded screenshot as its current image.

## Server side

Start the upload API from the repo root:

```bash
python streamlit_hotkey_bridge/upload_server.py --host 0.0.0.0 --port 8765
```

Start the Streamlit UI variant from the repo root:

```bash
streamlit run streamlit_hotkey_bridge/app.py
```

Uploaded screenshots are stored in `streamlit_hotkey_bridge/uploads/`.

## Local computer

Install the local client dependencies:

```bash
pip install -r streamlit_hotkey_bridge/local_requirements.txt
```

Run the hotkey listener and point it at your server:

```bash
python streamlit_hotkey_bridge/local_hotkey_client.py --server-url http://YOUR_SERVER_IP:8765
```

Now type `kk` on your local computer. The script will:

- save a local screenshot into `streamlit_hotkey_bridge/captures/`
- upload that file to the server
- let the Streamlit bridge app pick it up automatically on the next refresh cycle

## Notes

- Manual image upload still works in `streamlit_hotkey_bridge/app.py`; it only falls back to the newest remote screenshot when no manual file is selected.
- The bridge app reuses the same model inference flow and visualization module as `streamlit_ui/`.
- If your server is behind SSH, you can expose port `8765` with port forwarding and use `http://127.0.0.1:8765` as the client URL.
