from __future__ import annotations

import argparse
import base64
import importlib.util
import io
import json
import sys
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from uuid import uuid4

import torch
from PIL import Image, UnidentifiedImageError

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from aguvis_remote_bridge.common import (
    SERVER_LATEST_RESULT_PATH,
    SERVER_RESULT_DIR,
    SERVER_UPLOAD_DIR,
    atomic_write_json,
    ensure_server_state_dirs,
)

SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from aguvis.serve.cli import generate_response, load_pretrained_model

VALID_MODES = {"self-plan", "force-plan", "grounding"}


def resolve_attn_implementation(device: str) -> str:
    if device == "cuda" and importlib.util.find_spec("flash_attn") is not None:
        return "flash_attention_2"
    return "eager"


def resolve_torch_dtype(device: str):
    if device == "cuda":
        return torch.bfloat16
    return None


def decode_image(encoded_image: str) -> Image.Image:
    image_bytes = base64.b64decode(encoded_image, validate=True)
    return Image.open(io.BytesIO(image_bytes)).convert("RGB")


def choose_device(requested_device: str | None) -> str:
    if requested_device:
        return requested_device
    return "cuda" if torch.cuda.is_available() else "cpu"


def save_server_image(image: Image.Image, requested_filename: str | None) -> Path:
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    stem = Path(requested_filename or f"screenshot_{timestamp}").stem
    safe_stem = "".join(ch if ch.isalnum() or ch in {"_", "-", "."} else "_" for ch in stem).strip("._")
    safe_stem = safe_stem or "screenshot"
    final_path = SERVER_UPLOAD_DIR / f"{safe_stem}_{uuid4().hex[:8]}.png"
    image.save(final_path, format="PNG")
    return final_path


class AguvisInferenceHandler(BaseHTTPRequestHandler):
    server_version = "AguvisRemoteBridge/1.0"

    def do_GET(self) -> None:
        if self.path != "/health":
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return

        self.send_json(
            HTTPStatus.OK,
            {
                "status": "ok",
                "model_path": self.server.model_path,  # type: ignore[attr-defined]
                "device": self.server.device,  # type: ignore[attr-defined]
                "latest_result_path": str(SERVER_LATEST_RESULT_PATH),
            },
        )

    def do_POST(self) -> None:
        if self.path != "/infer":
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

        try:
            payload = json.loads(self.rfile.read(content_length))
        except json.JSONDecodeError as exc:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": f"Invalid JSON: {exc.msg}"})
            return

        try:
            response_payload = self.run_inference(payload)
        except ValueError as exc:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        except UnidentifiedImageError:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid image payload"})
            return
        except Exception as exc:  # pragma: no cover - best effort server guard
            self.send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
            return

        self.send_json(HTTPStatus.OK, response_payload)

    def run_inference(self, payload: dict[str, Any]) -> dict[str, Any]:
        encoded_image = payload.get("image_base64")
        if not isinstance(encoded_image, str) or not encoded_image.strip():
            raise ValueError("`image_base64` is required.")

        instruction = payload.get("instruction")
        if not isinstance(instruction, str) or not instruction.strip():
            raise ValueError("`instruction` is required.")

        mode = payload.get("mode", "grounding")
        if mode not in VALID_MODES:
            raise ValueError(f"`mode` must be one of {sorted(VALID_MODES)}.")

        previous_actions = payload.get("previous_actions")
        if previous_actions is not None and not isinstance(previous_actions, list):
            raise ValueError("`previous_actions` must be a list of strings or null.")

        low_level_instruction = payload.get("low_level_instruction")
        if low_level_instruction is not None and not isinstance(low_level_instruction, str):
            raise ValueError("`low_level_instruction` must be a string or null.")

        title = payload.get("title")
        if title is not None and not isinstance(title, str):
            raise ValueError("`title` must be a string or null.")

        image = decode_image(encoded_image)
        saved_image_path = save_server_image(image, payload.get("filename"))

        started_at = time.time()
        with self.server.inference_lock:  # type: ignore[attr-defined]
            result_text = generate_response(
                model=self.server.model,  # type: ignore[attr-defined]
                processor=self.server.processor,  # type: ignore[attr-defined]
                tokenizer=self.server.tokenizer,  # type: ignore[attr-defined]
                image=image,
                instruction=instruction,
                previous_actions=previous_actions,
                low_level_instruction=low_level_instruction,
                mode=mode,
                temperature=float(payload.get("temperature", 0.0)),
                max_new_tokens=int(payload.get("max_new_tokens", 512)),
            )
        duration_seconds = round(time.time() - started_at, 3)

        result_payload = {
            "status": "ok",
            "title": title,
            "instruction": instruction,
            "mode": mode,
            "previous_actions": previous_actions,
            "low_level_instruction": low_level_instruction,
            "result": result_text,
            "saved_image_path": str(saved_image_path),
            "duration_seconds": duration_seconds,
            "server_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        result_path = SERVER_RESULT_DIR / f"result_{time.strftime('%Y%m%d-%H%M%S')}_{uuid4().hex[:8]}.json"
        atomic_write_json(result_path, result_payload)
        atomic_write_json(SERVER_LATEST_RESULT_PATH, result_payload)
        return result_payload

    def send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args) -> None:
        return


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run AGUVIS inference as a remote HTTP server.")
    parser.add_argument("--host", default="0.0.0.0", help="Host interface to bind.")
    parser.add_argument("--port", type=int, default=8766, help="Port to listen on.")
    parser.add_argument("--model-path", default="xlangai/Aguvis-7B-720P", help="Model path or Hugging Face repo id.")
    parser.add_argument("--device", default=None, help="Inference device. Defaults to `cuda` when available.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_server_state_dirs()
    device = choose_device(args.device)
    print(f"Loading model `{args.model_path}` on `{device}`...")
    model, processor, tokenizer = load_pretrained_model(
        args.model_path,
        attn_implementation=resolve_attn_implementation(device),
        torch_dtype=resolve_torch_dtype(device),
    )
    model.to(device)
    model.tie_weights()

    server = ThreadingHTTPServer((args.host, args.port), AguvisInferenceHandler)
    server.model = model  # type: ignore[attr-defined]
    server.processor = processor  # type: ignore[attr-defined]
    server.tokenizer = tokenizer  # type: ignore[attr-defined]
    server.model_path = args.model_path  # type: ignore[attr-defined]
    server.device = device  # type: ignore[attr-defined]
    server.inference_lock = threading.Lock()  # type: ignore[attr-defined]

    print(f"AGUVIS inference server listening on http://{args.host}:{args.port}/infer")
    print(f"Server uploads are stored in {SERVER_UPLOAD_DIR}")
    server.serve_forever()


if __name__ == "__main__":
    main()
