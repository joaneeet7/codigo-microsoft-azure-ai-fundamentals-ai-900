from __future__ import annotations

import base64
import json
import os
import html
from pathlib import Path
from typing import Any

import requests
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent
ENV_PATH = ROOT_DIR / "backend" / ".env"
COMPONENT_DIR = ROOT_DIR / "streamlit_component" / "vision_lab"
vision_lab_component = components.declare_component("vision_lab", path=str(COMPONENT_DIR))
load_dotenv(ENV_PATH, override=True, encoding="utf-8-sig")

VISION_ENDPOINT = os.getenv("VISION_ENDPOINT", "").strip().rstrip("/")
VISION_KEY = os.getenv("VISION_KEY", "").strip()
VISION_API_VERSION = os.getenv("VISION_API_VERSION", "2024-02-01").strip()
PEOPLE_CONFIDENCE_THRESHOLD = float(os.getenv("PEOPLE_CONFIDENCE_THRESHOLD", "0.75"))

MAX_IMAGE_BYTES = 20 * 1024 * 1024
SUPPORTED_TYPES = {"image/png", "image/jpeg", "image/webp", "image/bmp", "image/gif"}
DEFAULT_FEATURES = ["caption", "denseCaptions", "tags", "objects", "read", "people"]
FEATURE_OPTIONS = [
    ("caption", "Caption"),
    ("denseCaptions", "Dense"),
    ("tags", "Tags"),
    ("objects", "Objects"),
    ("read", "OCR"),
    ("people", "People"),
    ("smartCrops", "Crops"),
]


def has_vision_config() -> bool:
    return bool(VISION_ENDPOINT and VISION_KEY)


def parse_features(features: list[str]) -> list[str]:
    selected = [item for item in features if item in {key for key, _ in FEATURE_OPTIONS}]
    return selected or DEFAULT_FEATURES


def validate_image(file_name: str, content_type: str, image_bytes: bytes) -> None:
    if not image_bytes:
        raise ValueError("Sube una imagen valida.")
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise ValueError("La imagen supera el limite de 20 MB.")
    if content_type not in SUPPORTED_TYPES:
        raise ValueError("Formato no soportado. Usa PNG, JPG, WEBP, BMP o GIF.")


def analyze_with_azure(file_name: str, content_type: str, image_bytes: bytes, features: list[str]) -> dict[str, Any]:
    url = f"{VISION_ENDPOINT}/computervision/imageanalysis:analyze"
    params = {
        "api-version": VISION_API_VERSION,
        "features": ",".join(features),
    }

    if "smartCrops" in features:
        params["smartcrops-aspect-ratios"] = "1.0,1.33,1.78"

    response = requests.post(
        url,
        params=params,
        headers={
            "Ocp-Apim-Subscription-Key": VISION_KEY,
            "Content-Type": content_type or "application/octet-stream",
        },
        data=image_bytes,
        timeout=120,
    )

    try:
        data = response.json()
    except ValueError as exc:
        raise ValueError("Azure devolvio una respuesta no JSON.") from exc

    if not response.ok:
        error = data.get("error", {}) if isinstance(data, dict) else {}
        message = error.get("message") if isinstance(error, dict) else None
        code = error.get("code") if isinstance(error, dict) else None
        header_code = response.headers.get("x-ms-error-code")
        detail = message or code or header_code or "No se pudo analizar la imagen."
        if header_code and header_code not in detail:
            detail = f"{detail} ({header_code})"
        raise ValueError(detail)

    return {
        "mode": "azure",
        "fileName": file_name,
        "contentType": content_type,
        "bytes": len(image_bytes),
        "features": features,
        "summary": summarize_result(data),
        "raw": data,
    }


def summarize_result(data: dict[str, Any]) -> dict[str, Any]:
    caption = data.get("captionResult", {}).get("text")
    tags = [item.get("name") for item in data.get("tagsResult", {}).get("values", [])[:10] if item.get("name")]
    objects = [item.get("tags", [{}])[0].get("name") for item in data.get("objectsResult", {}).get("values", [])[:8]]
    people_values = data.get("peopleResult", {}).get("values", []) or []
    people = len(
        [
            item
            for item in people_values
            if float(item.get("confidence", 0) or 0) >= PEOPLE_CONFIDENCE_THRESHOLD
        ]
    )
    dense = [item.get("text") for item in data.get("denseCaptionsResult", {}).get("values", [])[:5] if item.get("text")]
    read_lines = []

    for block in data.get("readResult", {}).get("blocks", []) or []:
        for line in block.get("lines", []) or []:
            text = line.get("text")
            if text:
                read_lines.append(text)

    return {
        "caption": caption,
        "tags": tags,
        "objects": [item for item in objects if item],
        "people": people,
        "denseCaptions": dense,
        "readLines": read_lines[:12],
    }


def analyze_locally(file_name: str, content_type: str, image_bytes: bytes, features: list[str]) -> dict[str, Any]:
    kb = max(1, round(len(image_bytes) / 1024))
    summary = {
        "caption": "Modo demo local: imagen recibida correctamente.",
        "tags": ["demo", "vision", "imagen"],
        "objects": [],
        "people": 0,
        "denseCaptions": [f"Archivo {file_name or 'sin nombre'} listo para analizar con Azure AI Vision."],
        "readLines": [],
    }

    return {
        "mode": "demo",
        "fileName": file_name,
        "contentType": content_type,
        "bytes": len(image_bytes),
        "features": features,
        "summary": summary,
        "raw": {
            "message": "Configura VISION_ENDPOINT y VISION_KEY para usar Azure AI Vision.",
            "fileSizeKb": kb,
        },
    }


def analyze_image(file_name: str, content_type: str, image_bytes: bytes, features: list[str]) -> dict[str, Any]:
    validate_image(file_name, content_type, image_bytes)
    selected_features = parse_features(features)

    if has_vision_config():
        return analyze_with_azure(file_name, content_type, image_bytes, selected_features)

    return analyze_locally(file_name, content_type, image_bytes, selected_features)


def icon(name: str) -> str:
    paths = {
        "scan": '<path d="M3 7V5a2 2 0 0 1 2-2h2"/><path d="M17 3h2a2 2 0 0 1 2 2v2"/><path d="M21 17v2a2 2 0 0 1-2 2h-2"/><path d="M7 21H5a2 2 0 0 1-2-2v-2"/><circle cx="12" cy="12" r="3"/><path d="M7 12s2-5 5-5 5 5 5 5-2 5-5 5-5-5-5-5Z"/>',
        "image": '<rect width="18" height="18" x="3" y="3" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.1-3.1a2 2 0 0 0-2.8 0L6 21"/>',
        "upload": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m17 8-5-5-5 5"/><path d="M12 3v12"/>',
        "spark": '<path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z"/>',
        "tags": '<path d="M12.6 2.6a2 2 0 0 0-1.4-.6H4a2 2 0 0 0-2 2v7.2a2 2 0 0 0 .6 1.4l8.8 8.8a2 2 0 0 0 2.8 0l7.2-7.2a2 2 0 0 0 0-2.8Z"/><circle cx="7.5" cy="7.5" r=".5"/>',
        "boxes": '<path d="m7.5 4.3 4.5 2.6 4.5-2.6"/><path d="M3 8.4 12 13l9-4.6"/><path d="M12 22V13"/><path d="m3 8.4 9-5.2 9 5.2v7.2l-9 5.2-9-5.2Z"/>',
        "users": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.9"/><path d="M16 3.1a4 4 0 0 1 0 7.8"/>',
        "type": '<polyline points="4 7 4 4 20 4 20 7"/><line x1="9" x2="15" y1="20" y2="20"/><line x1="12" x2="12" y1="4" y2="20"/>',
        "alert": '<circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/>',
    }
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" '
        f'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        f'stroke-linejoin="round">{paths[name]}</svg>'
    )


def image_data_url(content_type: str, image_bytes: bytes) -> str:
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{content_type};base64,{encoded}"


def decode_data_url(data_url: str) -> bytes:
    if "," not in data_url:
        raise ValueError("La imagen no llego en un formato valido.")
    return base64.b64decode(data_url.split(",", 1)[1])


def component_page_css() -> str:
    return """
<style>
header, [data-testid="stToolbar"], [data-testid="stDecoration"], #MainMenu, footer {
  display: none !important;
}
.stApp {
  background: #eef4fb;
}
.block-container {
  max-width: none;
  padding: 0;
}
iframe[title="vision_lab.vision_lab"] {
  display: block;
}
</style>
"""


def render_css() -> None:
    css = (ROOT_DIR / "frontend" / "src" / "styles.css").read_text(encoding="utf-8")
    extra_css = """
header, [data-testid="stToolbar"], [data-testid="stDecoration"], #MainMenu, footer {
  display: none !important;
}

.stApp {
  background:
    radial-gradient(circle at 13% 14%, rgba(14, 165, 233, 0.18), transparent 30%),
    radial-gradient(circle at 84% 18%, rgba(16, 185, 129, 0.14), transparent 28%),
    linear-gradient(135deg, #eff6ff 0%, #f8fbff 48%, #ecfdf5 100%);
}

.stApp::before {
  content: "";
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background-image:
    linear-gradient(rgba(23, 32, 51, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(23, 32, 51, 0.05) 1px, transparent 1px);
  background-size: 42px 42px;
  mask-image: linear-gradient(to bottom, rgba(0, 0, 0, 0.7), transparent 88%);
}

.block-container {
  position: relative;
  z-index: 1;
  max-width: 1540px;
  padding: clamp(14px, 2.4vw, 34px);
}

[data-testid="stVerticalBlock"] {
  gap: 1rem;
}

[data-testid="stFileUploader"] section {
  min-height: 136px;
  border: 1px dashed #93a8c8;
  border-radius: 8px;
  background: #f8fbff;
}

[data-testid="stFileUploader"] button {
  border-radius: 8px;
  font-weight: 900;
}

[data-testid="stMultiSelect"] div {
  border-radius: 8px;
}

[data-testid="stMultiSelect"] [data-baseweb="tag"] {
  border: 1px solid #0284c7;
  color: #075985;
  background: #e0f2fe;
  border-radius: 8px;
  font-weight: 900;
}

.stButton > button {
  min-height: 48px;
  width: 100%;
  border: 0;
  border-radius: 8px;
  color: #ffffff;
  background: #0284c7;
  cursor: pointer;
  font-weight: 900;
  box-shadow: 0 14px 28px rgba(2, 132, 199, 0.24);
}

.stButton > button:disabled {
  cursor: not-allowed;
  opacity: 0.48;
}

.streamlit-panel {
  border: 1px solid rgba(148, 163, 184, 0.56);
  border-radius: 8px;
  box-shadow: 0 24px 70px rgba(23, 32, 51, 0.12);
  background: rgba(255, 255, 255, 0.94);
  backdrop-filter: blur(12px);
  overflow: hidden;
}

.streamlit-panel-inner {
  padding: clamp(20px, 2vw, 28px);
}

.streamlit-input {
  border-top: 4px solid #0284c7;
}

.streamlit-result {
  border-top: 4px solid #10b981;
}

.stMultiSelect,
.stFileUploader,
.stButton {
  margin-bottom: 0;
}

.drop-zone {
  min-height: 260px;
}

@media (max-width: 900px) {
  .side-panel {
    min-height: 360px;
  }
}
"""
    st.html(f"<style>{css}\n{extra_css}</style>")


def render_html(fragment: str) -> None:
    st.html(fragment)


def result_card(icon_name: str, title: str, value: str) -> str:
    return (
        f'<article class="result-card">'
        f'<span>{icon(icon_name)}</span>'
        f"<div><strong>{html.escape(title)}</strong><p>{html.escape(value)}</p></div>"
        f"</article>"
    )


def render_details(title: str, items: list[str], empty: str, icon_name: str | None = None) -> str:
    title_icon = icon(icon_name) if icon_name else ""
    body = "".join(f"<p>{html.escape(item)}</p>" for item in items) if items else f"<p>{html.escape(empty)}</p>"
    return (
        f'<section class="detail-section">'
        f"<h3>{title_icon} {html.escape(title)}</h3>"
        f"{body}"
        f"</section>"
    )


def main() -> None:
    st.set_page_config(page_title="App Vision", page_icon=":camera:", layout="wide")
    st.html(component_page_css())

    if "result" not in st.session_state:
        st.session_state.result = None
    if "error" not in st.session_state:
        st.session_state.error = ""
    if "preview_data_url" not in st.session_state:
        st.session_state.preview_data_url = ""
    if "last_file_name" not in st.session_state:
        st.session_state.last_file_name = ""
    if "last_content_type" not in st.session_state:
        st.session_state.last_content_type = ""
    if "last_bytes" not in st.session_state:
        st.session_state.last_bytes = 0
    if "selected_features" not in st.session_state:
        st.session_state.selected_features = DEFAULT_FEATURES

    configured = has_vision_config()
    css = (ROOT_DIR / "frontend" / "src" / "styles.css").read_text(encoding="utf-8")
    payload = vision_lab_component(
        css=css,
        configured=configured,
        apiVersion=VISION_API_VERSION,
        result=st.session_state.result,
        error=st.session_state.error,
        previewDataUrl=st.session_state.preview_data_url,
        fileName=st.session_state.last_file_name,
        contentType=st.session_state.last_content_type,
        bytes=st.session_state.last_bytes,
        selectedFeatures=st.session_state.selected_features,
        default=None,
        key="vision-lab-v2",
    )

    if isinstance(payload, dict) and payload.get("action") == "analyze":
        st.session_state.error = ""
        st.session_state.result = None
        st.session_state.preview_data_url = payload.get("dataUrl", "")
        st.session_state.last_file_name = payload.get("fileName", "")
        st.session_state.last_content_type = payload.get("contentType", "")
        st.session_state.selected_features = parse_features(payload.get("features", []))

        try:
            image_bytes = decode_data_url(st.session_state.preview_data_url)
            st.session_state.last_bytes = len(image_bytes)
            st.session_state.result = analyze_image(
                st.session_state.last_file_name,
                st.session_state.last_content_type,
                image_bytes,
                st.session_state.selected_features,
            )
        except ValueError as exc:
            st.session_state.error = str(exc)

        st.rerun()


if __name__ == "__main__":
    main()
