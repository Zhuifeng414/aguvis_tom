from __future__ import annotations

import argparse
import threading
import time
from collections import deque
from pathlib import Path

import pyautogui
import requests
from pynput import keyboard

DEFAULT_TRIGGER = "kk"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "captures"


def normalize_upload_url(server_url: str) -> str:
    cleaned = server_url.rstrip("/")
    if cleaned.endswith("/upload"):
        return cleaned
    return f"{cleaned}/upload"


class ScreenshotHotkeyUploader:
    def __init__(
        self,
        server_url: str,
        output_dir: Path,
        trigger_sequence: str,
        debounce_seconds: float,
        request_timeout: float,
    ) -> None:
        self.upload_url = normalize_upload_url(server_url)
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.trigger_sequence = trigger_sequence.lower()
        self.debounce_seconds = debounce_seconds
        self.request_timeout = request_timeout
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
        worker = threading.Thread(target=self.capture_and_upload, daemon=True)
        worker.start()

    def capture_and_upload(self) -> None:
        if not self.capture_lock.acquire(blocking=False):
            print("Screenshot already in progress; skipping duplicate trigger.")
            return

        try:
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            image_path = self.output_dir / filename

            screenshot = pyautogui.screenshot()
            screenshot.save(image_path)
            print(f"Saved screenshot: {image_path}")

            with image_path.open("rb") as image_file:
                response = requests.post(
                    self.upload_url,
                    data=image_file.read(),
                    headers={
                        "Content-Type": "image/png",
                        "X-Filename": filename,
                    },
                    timeout=self.request_timeout,
                )
            response.raise_for_status()
            payload = response.json()
            print(f"Uploaded screenshot: {payload.get('path', 'unknown path')}")
        except Exception as exc:
            print(f"Upload failed: {exc}")
        finally:
            self.capture_lock.release()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture a screenshot when the hotkey sequence is typed.")
    parser.add_argument(
        "--server-url",
        required=True,
        help="Base server URL, for example http://YOUR_SERVER_IP:8765",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory where local screenshots are saved before upload.",
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
        default=30.0,
        help="Upload timeout in seconds.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    uploader = ScreenshotHotkeyUploader(
        server_url=args.server_url,
        output_dir=Path(args.output_dir).expanduser().resolve(),
        trigger_sequence=args.trigger_sequence,
        debounce_seconds=args.debounce_seconds,
        request_timeout=args.request_timeout,
    )
    print(f"Listening for hotkey sequence: {args.trigger_sequence}")
    print(f"Uploading screenshots to: {uploader.upload_url}")
    print(f"Saving local copies in: {uploader.output_dir}")
    with keyboard.Listener(on_press=uploader.on_press) as listener:
        listener.join()


if __name__ == "__main__":
    main()
