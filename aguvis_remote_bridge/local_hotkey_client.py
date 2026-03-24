from __future__ import annotations

import argparse
import sys
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any

import pyautogui
import requests
from pynput import keyboard

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from aguvis_remote_bridge.common import (
    DEFAULT_SERVER_URL,
    DEFAULT_TRIGGER,
    LATEST_RESULT_PATH,
    LOCAL_CAPTURE_DIR,
    LOCAL_RESULTS_DIR,
    SETTINGS_PATH,
    atomic_write_json,
    default_settings,
    encode_image_file,
    ensure_local_state_dirs,
    load_json,
)


def normalize_server_url(server_url: str) -> str:
    cleaned = server_url.rstrip("/")
    if cleaned.endswith("/infer"):
        return cleaned
    return f"{cleaned}/infer"


class ScreenshotHotkeyInferenceClient:
    def __init__(
        self,
        settings_path: Path,
        output_dir: Path,
        latest_result_path: Path,
        trigger_sequence: str,
        debounce_seconds: float,
        request_timeout: float,
        server_url_override: str | None = None,
    ) -> None:
        self.settings_path = settings_path
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.latest_result_path = latest_result_path
        self.results_dir = LOCAL_RESULTS_DIR
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.trigger_sequence = trigger_sequence.lower()
        self.debounce_seconds = debounce_seconds
        self.request_timeout = request_timeout
        self.server_url_override = server_url_override
        self.recent_chars: deque[str] = deque(maxlen=len(self.trigger_sequence))
        self.last_trigger_time = 0.0
        self.capture_lock = threading.Lock()

    def on_press(self, key) -> None:
        try:
            key_char = key.char.lower()
        except AttributeError:
            self.recent_chars.clear()
            return

        self.recent_chars.append(key_char)
        if "".join(self.recent_chars) != self.trigger_sequence:
            return

        now = time.monotonic()
        if now - self.last_trigger_time < self.debounce_seconds:
            self.recent_chars.clear()
            return

        self.last_trigger_time = now
        self.recent_chars.clear()
        worker = threading.Thread(target=self.capture_and_infer, daemon=True)
        worker.start()

    def load_settings(self) -> dict[str, Any]:
        settings = default_settings()
        saved_settings = load_json(self.settings_path) or {}
        settings.update(saved_settings)
        if self.server_url_override:
            settings["server_url"] = self.server_url_override
        return settings

    def capture_and_infer(self) -> None:
        if not self.capture_lock.acquire(blocking=False):
            print("Screenshot already in progress; skipping duplicate trigger.")
            return

        try:
            settings = self.load_settings()
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            image_path = self.output_dir / filename

            screenshot = pyautogui.screenshot()
            screenshot.save(image_path)
            print(f"Saved screenshot: {image_path}")

            request_payload = {
                "title": settings.get("title"),
                "instruction": settings.get("instruction"),
                "mode": settings.get("mode"),
                "previous_actions": settings.get("previous_actions"),
                "low_level_instruction": settings.get("low_level_instruction"),
                "temperature": settings.get("temperature", 0.0),
                "max_new_tokens": settings.get("max_new_tokens", 512),
                "filename": filename,
                "image_base64": encode_image_file(image_path),
            }

            server_url = normalize_server_url(str(settings.get("server_url", DEFAULT_SERVER_URL)))
            response = requests.post(server_url, json=request_payload, timeout=self.request_timeout)
            response.raise_for_status()
            server_payload = response.json()

            result_record = {
                "status": "ok",
                "captured_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "image_path": str(image_path),
                "server_url": server_url,
                "request": request_payload | {"image_base64": "<omitted>"},
                "response_text": server_payload.get("result", ""),
                "server_payload": server_payload,
            }
            self.persist_result(result_record, timestamp)
            print(f"Received model output in {server_payload.get('duration_seconds', 'unknown')}s")
        except Exception as exc:
            error_record = {
                "status": "error",
                "captured_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "image_path": str(image_path) if "image_path" in locals() else None,
                "server_url": normalize_server_url(self.load_settings().get("server_url", DEFAULT_SERVER_URL)),
                "response_text": "",
                "error": str(exc),
            }
            self.persist_result(error_record, time.strftime("%Y%m%d-%H%M%S"))
            print(f"Inference failed: {exc}")
        finally:
            self.capture_lock.release()

    def persist_result(self, result_record: dict[str, Any], timestamp: str) -> None:
        result_path = self.results_dir / f"result_{timestamp}.json"
        atomic_write_json(result_path, result_record)
        atomic_write_json(self.latest_result_path, result_record)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture a screenshot on `kk`, send it to the remote AGUVIS server, and save the latest result."
    )
    parser.add_argument(
        "--server-url",
        default=None,
        help="Optional override for the server base URL, for example http://YOUR_SERVER_IP:8766",
    )
    parser.add_argument(
        "--settings-file",
        default=str(SETTINGS_PATH),
        help="Path to the JSON file that the local Streamlit app writes.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(LOCAL_CAPTURE_DIR),
        help="Directory where local screenshots are saved.",
    )
    parser.add_argument(
        "--latest-result-file",
        default=str(LATEST_RESULT_PATH),
        help="JSON file used by the local Streamlit app to display the newest result.",
    )
    parser.add_argument(
        "--trigger-sequence",
        default=DEFAULT_TRIGGER,
        help="Character sequence that triggers a screenshot capture.",
    )
    parser.add_argument(
        "--debounce-seconds",
        type=float,
        default=1.0,
        help="Minimum time between two captures.",
    )
    parser.add_argument(
        "--request-timeout",
        type=float,
        default=120.0,
        help="HTTP timeout in seconds for remote inference.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_local_state_dirs()
    client = ScreenshotHotkeyInferenceClient(
        settings_path=Path(args.settings_file).expanduser().resolve(),
        output_dir=Path(args.output_dir).expanduser().resolve(),
        latest_result_path=Path(args.latest_result_file).expanduser().resolve(),
        trigger_sequence=args.trigger_sequence,
        debounce_seconds=args.debounce_seconds,
        request_timeout=args.request_timeout,
        server_url_override=args.server_url,
    )
    effective_server_url = client.load_settings().get("server_url", DEFAULT_SERVER_URL)
    print(f"Listening for hotkey sequence: {args.trigger_sequence}")
    print(f"Local screenshots are stored in: {client.output_dir}")
    print(f"Latest result JSON: {client.latest_result_path}")
    print(f"Remote inference endpoint: {normalize_server_url(str(effective_server_url))}")
    with keyboard.Listener(on_press=client.on_press) as listener:
        listener.join()


if __name__ == "__main__":
    main()
