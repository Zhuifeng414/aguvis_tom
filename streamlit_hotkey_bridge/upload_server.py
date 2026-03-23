from __future__ import annotations

import argparse
import json
import mimetypes
import re
import time
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BRIDGE_ROOT = Path(__file__).resolve().parent
DEFAULT_UPLOAD_DIR = BRIDGE_ROOT / "uploads"
ALLOWED_CONTENT_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
}


def safe_filename(filename: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", filename).strip("._")
    return cleaned or "screenshot"


def choose_suffix(content_type: str, filename: str | None) -> str:
    normalized = content_type.split(";", maxsplit=1)[0].strip().lower()
    if normalized in ALLOWED_CONTENT_TYPES:
        return ALLOWED_CONTENT_TYPES[normalized]

    if filename:
        guessed_type, _ = mimetypes.guess_type(filename)
        if guessed_type in ALLOWED_CONTENT_TYPES:
            return ALLOWED_CONTENT_TYPES[guessed_type]

    raise ValueError(f"Unsupported image type: {content_type or 'missing'}")


class UploadHandler(BaseHTTPRequestHandler):
    server_version = "AguvisScreenshotUpload/1.0"

    @property
    def upload_dir(self) -> Path:
        return self.server.upload_dir  # type: ignore[attr-defined]

    def do_GET(self) -> None:
        if self.path != "/health":
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return

        latest_file = self.latest_uploaded_file()
        payload = {
            "status": "ok",
            "upload_dir": str(self.upload_dir),
            "latest_file": str(latest_file) if latest_file else None,
        }
        self.send_json(HTTPStatus.OK, payload)

    def do_POST(self) -> None:
        if self.path != "/upload":
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return

        content_length_header = self.headers.get("Content-Length", "0")
        try:
            content_length = int(content_length_header)
        except ValueError:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid Content-Length header"})
            return

        if content_length <= 0:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Request body is empty"})
            return

        content_type = self.headers.get("Content-Type", "")
        requested_filename = self.headers.get("X-Filename")
        try:
            suffix = choose_suffix(content_type, requested_filename)
        except ValueError as exc:
            self.send_json(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"error": str(exc)})
            return

        body = self.rfile.read(content_length)
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        stem = requested_filename or f"screenshot_{timestamp}"
        final_name = f"{safe_filename(Path(stem).stem)}_{uuid.uuid4().hex[:8]}{suffix}"
        final_path = self.upload_dir / final_name
        temp_path = final_path.with_suffix(f"{final_path.suffix}.part")

        self.upload_dir.mkdir(parents=True, exist_ok=True)
        temp_path.write_bytes(body)
        temp_path.replace(final_path)

        self.send_json(
            HTTPStatus.CREATED,
            {
                "status": "saved",
                "filename": final_name,
                "path": str(final_path),
                "bytes": len(body),
            },
        )

    def log_message(self, format: str, *args) -> None:
        return

    def latest_uploaded_file(self) -> Path | None:
        candidates = sorted(
            [path for path in self.upload_dir.iterdir() if path.is_file()],
            key=lambda path: path.stat().st_mtime_ns,
            reverse=True,
        ) if self.upload_dir.exists() else []
        if not candidates:
            return None
        return candidates[0]

    def send_json(self, status: HTTPStatus, payload: dict[str, object]) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Accept raw image uploads for the Streamlit hotkey bridge.")
    parser.add_argument("--host", default="0.0.0.0", help="Host interface to bind.")
    parser.add_argument("--port", type=int, default=8765, help="Port to listen on.")
    parser.add_argument(
        "--upload-dir",
        default=str(DEFAULT_UPLOAD_DIR),
        help="Directory where uploaded screenshots are stored.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    upload_dir = Path(args.upload_dir).expanduser().resolve()
    server = ThreadingHTTPServer((args.host, args.port), UploadHandler)
    server.upload_dir = upload_dir  # type: ignore[attr-defined]
    print(f"Listening for uploads on http://{args.host}:{args.port}/upload")
    print(f"Saving screenshots into {upload_dir}")
    server.serve_forever()


if __name__ == "__main__":
    main()
