# AGUVIS Remote Bridge

This folder creates the split workflow requested in `task/todo/5_back_server_front.md` without changing
`streamlit_hotkey_bridge/` or `streamlit_ui/`.

## What it does

1. `server.py` runs on the Linux server and exposes `/infer` for AGUVIS model inference.
2. `local_hotkey_client.py` runs on the local computer, listens for the `kk` key sequence, saves a screenshot, and
   sends it to the remote backend.
3. `app.py` runs as a local Streamlit UI, watches the newest local result JSON, and displays both the screenshot and
   the backend response.

## Server side

Start the backend from the repo root on the Linux server:

```bash
python aguvis_remote_bridge/server.py --host 0.0.0.0 --port 8766 --model-path xlangai/Aguvis-7B-720P
```

Health check:

```bash
curl http://YOUR_SERVER_IP:8766/health

curl http://127.0.0.1:8766/health

ssh -J tuq24452@129.32.95.123 -L 8766:127.0.0.1:8766 tuq24452@129.32.95.51

ssh -J tuq24452@129.32.95.123 -p 22 tuq24452@129.32.95.51

ssh -J tuq24452@129.32.95.123 -L 8766:127.0.0.1:8766 tuq24452@129.32.95.51
```

The server stores uploaded screenshots and the latest result in:

- `aguvis_remote_bridge/server_state/uploads/`
- `aguvis_remote_bridge/server_state/results/`

## Local computer

Install the extra local dependencies:

```bash
pip install -r aguvis_remote_bridge/local_requirements.txt
```

Start the local Streamlit UI:

```bash
streamlit run aguvis_remote_bridge/app.py
```

In the Streamlit sidebar, set `Server URL` to your Linux server, for example:

```text
http://YOUR_SERVER_IP:8766
```

The UI writes those settings into:

```text
aguvis_remote_bridge/local_state/current_settings.json
```

Start the local hotkey client:

```bash
python aguvis_remote_bridge/local_hotkey_client.py
```

You can also override the server URL directly:

```bash
python aguvis_remote_bridge/local_hotkey_client.py --server-url http://YOUR_SERVER_IP:8766
```

## Workflow

1. Open the local Streamlit app.
2. Configure the request fields in the sidebar.
3. Start `local_hotkey_client.py`.
4. Type `kk` on the local computer.
5. The client saves a local `.png`, uploads it to the Linux server, waits for inference, then writes the newest result
   into `aguvis_remote_bridge/local_state/latest_result.json`.
6. The Streamlit app auto-refreshes and shows:
   - the newest screenshot
   - the backend response text
   - the visualization overlay for any returned coordinates

## Notes

- The local UI does not run AGUVIS inference itself.
- If the backend is slow, the local UI will update after the hotkey client receives the response.
- If you tunnel the server over SSH, use the forwarded local URL in the Streamlit sidebar, for example
  `http://127.0.0.1:8766`.
