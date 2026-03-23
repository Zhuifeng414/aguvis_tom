# AGUVIS Live Capture

This folder adds a live screenshot bridge without modifying `streamlit_ui/`.

## What It Adds

- `app.py`: a Streamlit app derived from the current UI, but it automatically uses the newest image found in `streamlit_live_capture/uploads/`
- `local_client/kk`: a local command you can type as `kk` to save a PNG screenshot on your local machine and upload it to the server through your existing SSH jump host

## Server App

From the repo root on the server:

```bash
streamlit run streamlit_live_capture/app.py
```

The app watches:

```text
/home/tuq24452/code/GUIAgent/aguvis/streamlit_live_capture/uploads
```

If no manual file is uploaded in the UI, the newest file in that folder becomes the current image automatically.

## Local `kk` Command

The local command depends on:

```bash
pip install mss
```

Make the script executable on your local machine:

```bash
chmod +x streamlit_live_capture/local_client/kk
```

If you want to type only `kk`, add it to your `PATH`, for example:

```bash
mkdir -p ~/bin
ln -sf /path/to/aguvis/streamlit_live_capture/local_client/kk ~/bin/kk
export PATH="$HOME/bin:$PATH"
```

Then run:

```bash
kk
```

By default it:

1. waits 1.5 seconds
2. saves a full-screen PNG in `~/.aguvis_kk_captures/`
3. uploads that PNG to `/home/tuq24452/code/GUIAgent/aguvis/streamlit_live_capture/uploads/`

## SSH Defaults

The local script already matches your current SSH path:

```text
jump host:  tuq24452@129.32.95.123
server:     tuq24452@129.32.95.51
remote dir: /home/tuq24452/code/GUIAgent/aguvis/streamlit_live_capture/uploads
```

Override them if needed:

```bash
kk --jump-host user@jump --remote-host user@server --remote-dir /some/other/folder
```

## Notes

- The Streamlit app checks for a newer uploaded image every 2 seconds.
- A manual upload in the UI still overrides the live capture image.
- `kk` uses your local `ssh` and `scp` commands, so your existing SSH keys or password flow continue to work.
