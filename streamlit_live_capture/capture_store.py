from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

SUPPORTED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


@dataclass(frozen=True)
class CaptureInfo:
    path: Path
    modified_at: datetime


def ensure_capture_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def list_capture_files(capture_dir: Path) -> list[Path]:
    ensure_capture_dir(capture_dir)
    return sorted(
        (
            path
            for path in capture_dir.iterdir()
            if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES
        ),
        key=lambda path: (path.stat().st_mtime_ns, path.name),
    )


def latest_capture(capture_dir: Path) -> CaptureInfo | None:
    capture_files = list_capture_files(capture_dir)
    if not capture_files:
        return None

    latest_path = capture_files[-1]
    return CaptureInfo(
        path=latest_path,
        modified_at=datetime.fromtimestamp(latest_path.stat().st_mtime),
    )


def describe_capture(capture: CaptureInfo | None) -> str:
    if capture is None:
        return "no capture available"
    timestamp = capture.modified_at.strftime("%Y-%m-%d %H:%M:%S")
    return f"{capture.path.name} ({timestamp})"
