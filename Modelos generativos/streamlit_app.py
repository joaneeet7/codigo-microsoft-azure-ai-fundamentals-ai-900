import base64
import os
import textwrap
from html import escape
from pathlib import Path
from typing import Any, Literal

import requests
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent
ENV_PATH = ROOT_DIR / "backend" / ".env"
COMPONENT_DIR = ROOT_DIR / "streamlit_component" / "image_studio"
image_studio_component = components.declare_component("image_studio", path=str(COMPONENT_DIR))
load_dotenv(ENV_PATH, override=True, encoding="utf-8-sig")

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip().rstrip("/")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "").strip()
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-image-1").strip()
AZURE_OPENAI_MODEL_NAME = os.getenv("AZURE_OPENAI_MODEL_NAME", AZURE_OPENAI_DEPLOYMENT_NAME).strip()
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview").strip()
IMAGE_PROVIDER = os.getenv("IMAGE_PROVIDER", "").strip().lower()

ImageSize = Literal["1024x1024", "1024x1536", "1536x1024"]
ImageQuality = Literal["low", "medium", "high"]
VALID_SIZES = {"1024x1024", "1024x1536", "1536x1024"}
VALID_QUALITIES = {"low", "medium", "high"}


def has_azure_config() -> bool:
    return bool(AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY and AZURE_OPENAI_DEPLOYMENT_NAME)


def resolved_provider() -> str:
    if IMAGE_PROVIDER in {"azure-openai", "mai"}:
        return IMAGE_PROVIDER
    if AZURE_OPENAI_DEPLOYMENT_NAME.lower().startswith("mai-") or AZURE_OPENAI_MODEL_NAME.lower().startswith("mai-"):
        return "mai"
    return "azure-openai"


def normalize_mai_endpoint(endpoint: str) -> str:
    if endpoint.endswith(".services.ai.azure.com"):
        return endpoint
    return endpoint.replace(".cognitiveservices.azure.com", ".services.ai.azure.com")


def mai_dimensions(size: ImageSize) -> tuple[int, int]:
    if size == "1536x1024":
        return 1344, 768
    if size == "1024x1536":
        return 768, 1344
    return 1024, 1024


def validate_payload(prompt: str, size: str, quality: str) -> tuple[str, ImageSize, ImageQuality]:
    clean_prompt = (prompt or "").strip()
    if len(clean_prompt) < 3:
        raise ValueError("Escribe un prompt de al menos 3 caracteres.")
    if len(clean_prompt) > 4000:
        raise ValueError("El prompt supera el limite de 4000 caracteres.")
    if size not in VALID_SIZES:
        raise ValueError("Tamano no soportado.")
    if quality not in VALID_QUALITIES:
        raise ValueError("Calidad no soportada.")
    return clean_prompt, size, quality  # type: ignore[return-value]


def generate_image(prompt: str, size: str, quality: str) -> dict[str, Any]:
    clean_prompt, clean_size, clean_quality = validate_payload(prompt, size, quality)

    if has_azure_config():
        if resolved_provider() == "mai":
            return generate_with_mai(clean_prompt, clean_size, clean_quality)
        return generate_with_azure_openai(clean_prompt, clean_size, clean_quality)

    return generate_demo_image(clean_prompt, clean_size, clean_quality)


def generate_with_mai(prompt: str, size: ImageSize, quality: ImageQuality) -> dict[str, Any]:
    endpoint = normalize_mai_endpoint(AZURE_OPENAI_ENDPOINT)
    width, height = mai_dimensions(size)
    url = f"{endpoint}/mai/v1/images/generations"

    try:
        response = requests.post(
            url,
            headers={
                "api-key": AZURE_OPENAI_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "model": AZURE_OPENAI_DEPLOYMENT_NAME,
                "prompt": prompt,
                "width": width,
                "height": height,
            },
            timeout=120,
        )
    except requests.RequestException as exc:
        raise ValueError("No se pudo conectar con Azure para generar la imagen. Revisa endpoint, red y credenciales.") from exc

    data = parse_json_response(response)
    if not response.ok:
        raise_azure_error(response, data)

    return {
        "mode": "azure",
        "image": extract_image_src(data),
        "prompt": prompt,
        "size": f"{width}x{height}",
        "quality": quality,
        "deployment": AZURE_OPENAI_DEPLOYMENT_NAME,
    }


def generate_with_azure_openai(prompt: str, size: ImageSize, quality: ImageQuality) -> dict[str, Any]:
    url = (
        f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/"
        f"{AZURE_OPENAI_DEPLOYMENT_NAME}/images/generations"
        f"?api-version={AZURE_OPENAI_API_VERSION}"
    )

    try:
        response = requests.post(
            url,
            headers={
                "api-key": AZURE_OPENAI_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "prompt": prompt,
                "n": 1,
                "size": size,
                "quality": quality,
            },
            timeout=120,
        )
    except requests.RequestException as exc:
        raise ValueError("No se pudo conectar con Azure para generar la imagen. Revisa endpoint, red y credenciales.") from exc

    data = parse_json_response(response)
    if not response.ok:
        raise_azure_error(response, data)

    return {
        "mode": "azure",
        "image": extract_image_src(data),
        "prompt": prompt,
        "size": size,
        "quality": quality,
        "deployment": AZURE_OPENAI_DEPLOYMENT_NAME,
    }


def parse_json_response(response: requests.Response) -> dict[str, Any]:
    try:
        return response.json()
    except ValueError as exc:
        raise ValueError("Azure devolvio una respuesta no JSON.") from exc


def raise_azure_error(response: requests.Response, data: dict[str, Any]) -> None:
    error = data.get("error")
    if isinstance(error, dict):
        message = error.get("message") or error.get("code")
    else:
        message = data.get("message") or data.get("detail")
    raise ValueError(translate_azure_error(message or "No se pudo generar la imagen en Azure."))


def translate_azure_error(message: str) -> str:
    normalized = message.lower()
    if "deployment" in normalized and "does not exist" in normalized:
        return (
            f"El deployment '{AZURE_OPENAI_DEPLOYMENT_NAME}' no existe o todavia no esta disponible en Azure. "
            "Verifica que el nombre en backend\\.env coincida exactamente con el deployment creado en Azure AI Foundry. "
            "Si lo acabas de crear, espera unos minutos y vuelve a intentar."
        )
    if "api deployment" in normalized and "does not exist" in normalized:
        return (
            f"El deployment '{AZURE_OPENAI_DEPLOYMENT_NAME}' no existe o todavia no esta disponible en Azure. "
            "Revisa el nombre del deployment en Azure AI Foundry y en backend\\.env."
        )
    if "unauthorized" in normalized or "access denied" in normalized or "permission" in normalized:
        return "Azure rechazo la solicitud por permisos o credenciales. Revisa AZURE_OPENAI_API_KEY y el acceso al recurso."
    if "not found" in normalized:
        return "Azure no encontro el recurso o deployment configurado. Revisa endpoint, deployment y region."
    if "rate limit" in normalized or "too many requests" in normalized:
        return "Azure esta limitando las solicitudes. Espera un momento y vuelve a intentar."
    return message


def extract_image_src(data: dict[str, Any]) -> str:
    image = data.get("data", [{}])[0]
    b64_image = image.get("b64_json")
    image_url = image.get("url")

    if b64_image:
        return f"data:image/png;base64,{b64_image}"
    if image_url:
        return image_url
    raise ValueError("Azure no devolvio imagen.")


def generate_demo_image(prompt: str, size: ImageSize, quality: ImageQuality) -> dict[str, Any]:
    width, height = [int(part) for part in size.split("x")]
    title = escape(prompt[:90])
    wrapped = textwrap.wrap(prompt, width=32)[:5]
    lines = "".join(
        f'<text x="72" y="{270 + index * 52}" class="prompt">{escape(line)}</text>'
        for index, line in enumerate(wrapped)
    )
    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
      <defs>
        <linearGradient id="bg" x1="0" x2="1" y1="0" y2="1">
          <stop offset="0" stop-color="#172554"/>
          <stop offset="0.45" stop-color="#2563eb"/>
          <stop offset="1" stop-color="#14b8a6"/>
        </linearGradient>
        <radialGradient id="orb" cx="70%" cy="25%" r="55%">
          <stop offset="0" stop-color="#ffffff" stop-opacity="0.55"/>
          <stop offset="1" stop-color="#ffffff" stop-opacity="0"/>
        </radialGradient>
        <style>
          .label {{ font: 700 28px Inter, Arial, sans-serif; fill: #bfdbfe; letter-spacing: 0; }}
          .title {{ font: 900 76px Inter, Arial, sans-serif; fill: white; letter-spacing: 0; }}
          .prompt {{ font: 600 34px Inter, Arial, sans-serif; fill: #e0f2fe; letter-spacing: 0; }}
          .small {{ font: 700 24px Inter, Arial, sans-serif; fill: #ccfbf1; letter-spacing: 0; }}
        </style>
      </defs>
      <rect width="100%" height="100%" fill="url(#bg)"/>
      <circle cx="{width * 0.75}" cy="{height * 0.22}" r="{min(width, height) * 0.38}" fill="url(#orb)"/>
      <rect x="48" y="48" width="{width - 96}" height="{height - 96}" rx="34" fill="none" stroke="#ffffff" stroke-opacity="0.36" stroke-width="3"/>
      <text x="72" y="118" class="label">Modo demo local</text>
      <text x="72" y="205" class="title">Salida visual</text>
      {lines}
      <text x="72" y="{height - 92}" class="small">{escape(size)} - calidad {escape(quality)} - configura Azure para imagen real</text>
    </svg>
    """
    encoded = base64.b64encode(svg.encode("utf-8")).decode("utf-8")

    return {
        "mode": "demo",
        "image": f"data:image/svg+xml;base64,{encoded}",
        "prompt": title,
        "size": size,
        "quality": quality,
        "deployment": "demo-local",
    }


def page_css() -> str:
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
iframe[title="image_studio.image_studio"] {
  display: block;
}
</style>
"""


def main() -> None:
    st.set_page_config(page_title="Modelos Generativos", page_icon=":art:", layout="wide")
    st.html(page_css())

    if "result" not in st.session_state:
        st.session_state.result = None
    if "history" not in st.session_state:
        st.session_state.history = []
    if "error" not in st.session_state:
        st.session_state.error = ""
    if "last_request_id" not in st.session_state:
        st.session_state.last_request_id = ""
    if "completed_request_id" not in st.session_state:
        st.session_state.completed_request_id = ""

    css = (ROOT_DIR / "frontend" / "src" / "styles.css").read_text(encoding="utf-8")
    payload = image_studio_component(
        css=css,
        configured=has_azure_config(),
        deployment=AZURE_OPENAI_DEPLOYMENT_NAME,
        model=AZURE_OPENAI_MODEL_NAME,
        provider=resolved_provider(),
        apiVersion=AZURE_OPENAI_API_VERSION,
        result=st.session_state.result,
        history=st.session_state.history,
        error=st.session_state.error,
        completedRequestId=st.session_state.completed_request_id,
        default=None,
        key="image-studio-v3",
    )

    if (
        isinstance(payload, dict)
        and payload.get("action") == "generate"
        and payload.get("requestId")
        and payload.get("requestId") != st.session_state.last_request_id
    ):
        st.session_state.last_request_id = payload.get("requestId")
        st.session_state.error = ""
        try:
            result = generate_image(
                payload.get("prompt", ""),
                payload.get("size", "1024x1024"),
                payload.get("quality", "medium"),
            )
            st.session_state.result = result
            st.session_state.history = [result, *st.session_state.history][:6]
        except ValueError as exc:
            st.session_state.error = str(exc)
        except Exception as exc:
            st.session_state.error = f"Ocurrio un error inesperado al generar la imagen: {exc}"
        finally:
            st.session_state.completed_request_id = payload.get("requestId")
        st.rerun()


if __name__ == "__main__":
    main()
