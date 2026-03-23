from __future__ import annotations

import base64
import json
import re
from io import BytesIO

import streamlit.components.v1 as components
from PIL import Image

COORDINATE_PAIR_PATTERN = re.compile(r"\(\s*([-+]?\d*\.?\d+)\s*,\s*([-+]?\d*\.?\d+)\s*\)")
NAMED_COORDINATE_PATTERN = re.compile(
    r"x\s*=\s*([-+]?\d*\.?\d+)\s*[, ]+\s*y\s*=\s*([-+]?\d*\.?\d+)",
    re.IGNORECASE,
)


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def extract_action_points(action_text: str | None) -> list[dict[str, float | str]]:
    if not action_text:
        return []

    points: list[dict[str, float | str]] = []
    for index, match in enumerate(COORDINATE_PAIR_PATTERN.finditer(action_text), start=1):
        x = clamp01(float(match.group(1)))
        y = clamp01(float(match.group(2)))
        points.append({"label": f"P{index}", "x": x, "y": y})

    if points:
        return points

    for index, match in enumerate(NAMED_COORDINATE_PATTERN.finditer(action_text), start=1):
        x = clamp01(float(match.group(1)))
        y = clamp01(float(match.group(2)))
        points.append({"label": f"P{index}", "x": x, "y": y})

    return points


def image_to_data_url(image: Image.Image) -> str:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def compute_component_height(image: Image.Image) -> int:
    width, height = image.size
    assumed_render_width = 700
    frame_height = int(assumed_render_width * height / max(width, 1))
    return max(360, min(frame_height + 56, 1400))


def render_action_visualization(
    image: Image.Image,
    action_text: str | None,
    *,
    height: int | None = None,
) -> list[dict[str, float | str]]:
    points = extract_action_points(action_text)
    image_url = image_to_data_url(image)
    points_json = json.dumps(points)
    show_swipe_line = "true" if len(points) >= 2 and action_text and "swipe" in action_text.lower() else "false"
    component_height = compute_component_height(image) if height is None else height

    html_payload = f"""
    <div class="viz-root">
      <div class="viz-frame" id="viz-frame">
        <img id="viz-image" src="{image_url}" alt="Action visualization" />
        <svg id="viz-overlay" viewBox="0 0 1000 1000" preserveAspectRatio="none"></svg>
        <div class="viz-coordinates" id="viz-coordinates">x: -, y: -</div>
      </div>
      <div class="viz-caption">Hover over the image to inspect normalized coordinates.</div>
    </div>

    <style>
      html, body {{
        margin: 0;
        padding: 0;
        background: transparent;
        color: #e5e7eb;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      }}
      .viz-root {{
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
      }}
      .viz-frame {{
        position: relative;
        width: 100%;
        border: 1px solid rgba(148, 163, 184, 0.45);
        border-radius: 14px;
        overflow: hidden;
        background: #0f172a;
      }}
      .viz-frame img {{
        display: block;
        width: 100%;
        height: auto;
      }}
      .viz-frame svg {{
        position: absolute;
        inset: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
      }}
      .viz-coordinates {{
        position: absolute;
        top: 12px;
        left: 12px;
        padding: 6px 10px;
        border-radius: 999px;
        background: rgba(15, 23, 42, 0.82);
        color: #f8fafc;
        font-size: 12px;
        letter-spacing: 0.02em;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(248, 250, 252, 0.18);
      }}
      .viz-caption {{
        font-size: 0.92rem;
        color: #94a3b8;
      }}
    </style>

    <script>
      const points = {points_json};
      const overlay = document.getElementById("viz-overlay");
      const frame = document.getElementById("viz-frame");
      const coords = document.getElementById("viz-coordinates");
      const showSwipeLine = {show_swipe_line};
      const SVG_NS = "http://www.w3.org/2000/svg";

      function appendSvgElement(tagName, attributes) {{
        const element = document.createElementNS(SVG_NS, tagName);
        Object.entries(attributes).forEach(([key, value]) => element.setAttribute(key, String(value)));
        overlay.appendChild(element);
        return element;
      }}

      if (showSwipeLine && points.length >= 2) {{
        appendSvgElement("line", {{
          x1: points[0].x * 1000,
          y1: points[0].y * 1000,
          x2: points[1].x * 1000,
          y2: points[1].y * 1000,
          stroke: "#fb7185",
          "stroke-width": 5,
          "stroke-dasharray": "16 12",
          "stroke-linecap": "round",
          opacity: 0.92
        }});
      }}

      points.forEach((point) => {{
        const cx = point.x * 1000;
        const cy = point.y * 1000;
        appendSvgElement("rect", {{
          x: cx - 22,
          y: cy - 22,
          width: 44,
          height: 44,
          rx: 6,
          ry: 6,
          fill: "rgba(0, 0, 0, 0.1)",
          stroke: "#ef4444",
          "stroke-width": 6
        }});
        appendSvgElement("circle", {{
          cx,
          cy,
          r: 6,
          fill: "#ef4444"
        }});
        appendSvgElement("text", {{
          x: cx + 28,
          y: cy - 24,
          fill: "#fee2e2",
          "font-size": 28,
          "font-weight": 700
        }}).textContent = point.label;
      }});

      const crosshairX = appendSvgElement("line", {{
        x1: 0,
        y1: 0,
        x2: 0,
        y2: 1000,
        stroke: "#38bdf8",
        "stroke-width": 2,
        opacity: 0
      }});

      const crosshairY = appendSvgElement("line", {{
        x1: 0,
        y1: 0,
        x2: 1000,
        y2: 0,
        stroke: "#38bdf8",
        "stroke-width": 2,
        opacity: 0
      }});

      function setCrosshairVisibility(visible) {{
        const opacity = visible ? 0.95 : 0;
        crosshairX.setAttribute("opacity", opacity);
        crosshairY.setAttribute("opacity", opacity);
      }}

      frame.addEventListener("mousemove", (event) => {{
        const rect = frame.getBoundingClientRect();
        const x = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width));
        const y = Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height));

        coords.textContent = `x: ${{x.toFixed(4)}}, y: ${{y.toFixed(4)}}`;
        crosshairX.setAttribute("x1", x * 1000);
        crosshairX.setAttribute("x2", x * 1000);
        crosshairY.setAttribute("y1", y * 1000);
        crosshairY.setAttribute("y2", y * 1000);
        setCrosshairVisibility(true);
      }});

      frame.addEventListener("mouseleave", () => {{
        coords.textContent = "x: -, y: -";
        setCrosshairVisibility(false);
      }});
    </script>
    """

    components.html(html_payload, height=component_height, scrolling=False)
    return points
