import base64
import os
from pathlib import Path
from typing import Any

import requests
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent
ENV_PATH = ROOT_DIR / "backend" / ".env"
COMPONENT_DIR = ROOT_DIR / "streamlit_component" / "visual_interpreter"
visual_interpreter_component = components.declare_component("visual_interpreter", path=str(COMPONENT_DIR))
load_dotenv(ENV_PATH, override=True, encoding="utf-8-sig")

MICROSOFT_FOUNDRY_ENDPOINT = os.getenv("MICROSOFT_FOUNDRY_ENDPOINT", "").strip().rstrip("/")
MICROSOFT_FOUNDRY_API_KEY = os.getenv("MICROSOFT_FOUNDRY_API_KEY", "").strip()
MICROSOFT_FOUNDRY_DEPLOYMENT_NAME = os.getenv("MICROSOFT_FOUNDRY_DEPLOYMENT_NAME", "gpt-4o-mini").strip()
MICROSOFT_FOUNDRY_API_VERSION = os.getenv("MICROSOFT_FOUNDRY_API_VERSION", "2024-10-21").strip()
AZURE_IMAGE_DETAIL = os.getenv("AZURE_IMAGE_DETAIL", "low").strip().lower()

MAX_IMAGE_BYTES = 20 * 1024 * 1024
SUPPORTED_TYPES = {"image/png", "image/jpeg", "image/webp"}


def has_azure_config() -> bool:
    return bool(MICROSOFT_FOUNDRY_ENDPOINT and MICROSOFT_FOUNDRY_API_KEY and MICROSOFT_FOUNDRY_DEPLOYMENT_NAME)


def validate_image(file_name: str, content_type: str, image_bytes: bytes) -> None:
    if not image_bytes:
        raise ValueError("Sube una imagen valida.")
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise ValueError("La imagen supera el limite de 20 MB.")
    if content_type not in SUPPORTED_TYPES:
        raise ValueError("Formato no soportado. Usa PNG, JPG o WEBP.")
    if not file_name:
        raise ValueError("Selecciona una imagen valida.")


def analyze_visual(prompt: str, file_name: str, content_type: str, image_bytes: bytes) -> dict[str, Any]:
    clean_prompt = (prompt or "").strip()
    if len(clean_prompt) < 3:
        raise ValueError("Escribe un prompt de al menos 3 caracteres.")
    if len(clean_prompt) > 4000:
        raise ValueError("El prompt supera el limite de 4000 caracteres.")

    validate_image(file_name, content_type, image_bytes)

    if has_azure_config():
        return analyze_with_azure(clean_prompt, file_name, content_type, image_bytes)

    return analyze_locally(clean_prompt, file_name, content_type, image_bytes)


def analyze_with_azure(prompt: str, file_name: str, content_type: str, image_bytes: bytes) -> dict[str, Any]:
    image_data = base64.b64encode(image_bytes).decode("utf-8")
    detail = AZURE_IMAGE_DETAIL if AZURE_IMAGE_DETAIL in {"low", "high", "auto"} else "low"
    url = (
        f"{MICROSOFT_FOUNDRY_ENDPOINT}/openai/deployments/"
        f"{MICROSOFT_FOUNDRY_DEPLOYMENT_NAME}/chat/completions"
        f"?api-version={MICROSOFT_FOUNDRY_API_VERSION}"
    )

    try:
        response = requests.post(
            url,
            headers={
                "api-key": MICROSOFT_FOUNDRY_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "messages": [
                    {
                        "role": "system",
                        "content": "Eres un asistente experto en interpretar imagenes para prompts visuales. Responde en espanol, con observaciones accionables y buen criterio visual.",
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{content_type};base64,{image_data}",
                                    "detail": detail,
                                },
                            },
                        ],
                    },
                ],
                "max_tokens": 700,
                "temperature": 0.35,
            },
            timeout=120,
        )
    except requests.RequestException as exc:
        raise ValueError("No se pudo conectar con Azure. Revisa endpoint, red y credenciales.") from exc

    data = parse_json_response(response)
    if not response.ok:
        raise_azure_error(response, data)

    answer = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not answer:
        raise ValueError("Azure no devolvio una interpretacion.")

    return {
        "mode": "azure",
        "analysis": answer,
        "fileName": file_name,
        "contentType": content_type,
        "bytes": len(image_bytes),
        "deployment": MICROSOFT_FOUNDRY_DEPLOYMENT_NAME,
    }


def parse_json_response(response: requests.Response) -> dict[str, Any]:
    try:
        return response.json()
    except ValueError as exc:
        raise ValueError("Azure devolvio una respuesta no JSON.") from exc


def raise_azure_error(response: requests.Response, data: dict[str, Any]) -> None:
    error = data.get("error", {}) if isinstance(data, dict) else {}
    code = error.get("code") if isinstance(error, dict) else None
    message = error.get("message") if isinstance(error, dict) else None
    retry_after = response.headers.get("retry-after") or response.headers.get("Retry-After")
    detail = translate_azure_error(message or str(code or "No se pudo interpretar la imagen."))

    if retry_after:
        detail = f"{detail} Intenta de nuevo en {retry_after} segundos."

    raise ValueError(detail)


def translate_azure_error(message: str) -> str:
    normalized = message.lower()
    if "deployment" in normalized and "does not exist" in normalized:
        return (
            f"El deployment '{MICROSOFT_FOUNDRY_DEPLOYMENT_NAME}' no existe o todavia no esta disponible en Azure. "
            "Verifica que el nombre en backend\\.env coincida exactamente con el deployment creado."
        )
    if "unauthorized" in normalized or "access denied" in normalized or "permission" in normalized:
        return "Azure rechazo la solicitud por permisos o credenciales. Revisa MICROSOFT_FOUNDRY_API_KEY y el acceso al recurso."
    if "content filter" in normalized or "filtered" in normalized:
        return "Azure bloqueo la solicitud por filtros de contenido. Ajusta el prompt o usa otra imagen."
    if "rate limit" in normalized or "too many requests" in normalized:
        return "Azure esta limitando las solicitudes. Espera un momento y vuelve a intentar."
    if "not found" in normalized:
        return "Azure no encontro el recurso o deployment configurado. Revisa endpoint, deployment y region."
    return message


def analyze_locally(prompt: str, file_name: str, content_type: str, image_bytes: bytes) -> dict[str, Any]:
    kb = max(1, round(len(image_bytes) / 1024))
    answer = (
        "Modo demo local: el backend recibio la imagen y el prompt correctamente.\n\n"
        f"Archivo: {file_name or 'sin nombre'} ({content_type}, {kb} KB).\n\n"
        "Cuando configures Azure OpenAI con un deployment multimodal, esta misma pantalla devolvera una interpretacion real de la imagen. "
        "Prompt recibido:\n"
        f"{prompt}"
    )

    return {
        "mode": "demo",
        "analysis": answer,
        "fileName": file_name,
        "contentType": content_type,
        "bytes": len(image_bytes),
        "deployment": "demo-local",
    }


def decode_data_url(data_url: str) -> bytes:
    if "," not in data_url:
        raise ValueError("La imagen no llego en un formato valido.")
    return base64.b64decode(data_url.split(",", 1)[1])


def page_css() -> str:
    return """
<style>
header, [data-testid="stToolbar"], [data-testid="stDecoration"], #MainMenu, footer {
  display: none !important;
}
.stApp {
  background: #edf4fb;
}
.block-container {
  max-width: none;
  padding: 0;
}
iframe[title="visual_interpreter.visual_interpreter"] {
  display: block;
}
</style>
"""


def main() -> None:
    st.set_page_config(page_title="Visual Input", page_icon=":camera:", layout="wide")
    st.html(page_css())

    if "result" not in st.session_state:
        st.session_state.result = None
    if "error" not in st.session_state:
        st.session_state.error = ""
    if "last_request_id" not in st.session_state:
        st.session_state.last_request_id = ""
    if "completed_request_id" not in st.session_state:
        st.session_state.completed_request_id = ""

    css = (ROOT_DIR / "frontend" / "src" / "styles.css").read_text(encoding="utf-8")
    payload = visual_interpreter_component(
        css=css,
        configured=has_azure_config(),
        deployment=MICROSOFT_FOUNDRY_DEPLOYMENT_NAME,
        apiVersion=MICROSOFT_FOUNDRY_API_VERSION,
        result=st.session_state.result,
        error=st.session_state.error,
        completedRequestId=st.session_state.completed_request_id,
        default=None,
        key="visual-interpreter-v1",
    )

    if (
        isinstance(payload, dict)
        and payload.get("action") == "analyze"
        and payload.get("requestId")
        and payload.get("requestId") != st.session_state.last_request_id
    ):
        st.session_state.last_request_id = payload.get("requestId")
        st.session_state.error = ""
        st.session_state.result = None

        try:
            image_bytes = decode_data_url(payload.get("dataUrl", ""))
            st.session_state.result = analyze_visual(
                payload.get("prompt", ""),
                payload.get("fileName", ""),
                payload.get("contentType", ""),
                image_bytes,
            )
        except ValueError as exc:
            st.session_state.error = str(exc)
        except Exception as exc:
            st.session_state.error = f"Ocurrio un error inesperado al interpretar la imagen: {exc}"
        finally:
            st.session_state.completed_request_id = payload.get("requestId")
        st.rerun()


if __name__ == "__main__":
    main()
