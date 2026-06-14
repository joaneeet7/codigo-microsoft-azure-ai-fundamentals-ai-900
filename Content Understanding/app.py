import os
import time
import base64
from typing import Any

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv


load_dotenv()


FIELD_LABELS = {
    "nombre": "Nombre",
    "empresa": "Empresa",
    "correo": "Correo",
    "telefono": "Telefono",
    "servicio_solicitado": "Servicio solicitado",
    "presupuesto_estimado": "Presupuesto estimado",
    "fecha": "Fecha",
    "comentarios": "Comentarios",
}


# Analizadores predefinidos de Azure Content Understanding por modalidad.
# - Imagenes y documentos se procesan con OCR Read (prebuilt-read).
# - Audio y video usan los analizadores predefinidos de transcripcion.
# Cada uno se puede sobreescribir por variable de entorno.
DEFAULT_ANALYZERS = {
    "document": "prebuilt-read",
    "image": "prebuilt-read",
    "audio": "prebuilt-audioSearch",
    "video": "prebuilt-videoSearch",
}

ANALYZER_ENV_VARS = {
    "document": "AZURE_CU_DOCUMENT_ANALYZER_ID",
    "image": "AZURE_CU_IMAGE_ANALYZER_ID",
    "audio": "AZURE_CU_AUDIO_ANALYZER_ID",
    "video": "AZURE_CU_VIDEO_ANALYZER_ID",
}

MODALITY_LABELS = {
    "document": "Documento (OCR Read)",
    "image": "Imagen (OCR Read)",
    "audio": "Audio (transcripcion)",
    "video": "Video (transcripcion)",
}

IMAGE_EXTS = {"png", "jpg", "jpeg", "bmp", "tif", "tiff", "gif", "webp"}
AUDIO_EXTS = {"mp3", "wav", "m4a", "aac", "ogg", "flac"}
VIDEO_EXTS = {"mp4", "mov", "avi", "mkv", "webm", "m4v"}
DOCUMENT_EXTS = {"pdf", "txt", "docx", "doc", "rtf", "html", "htm", "md"}


def has_azure_config() -> bool:
    required = [
        "AZURE_CONTENT_UNDERSTANDING_ENDPOINT",
        "AZURE_CONTENT_UNDERSTANDING_KEY",
    ]
    return all(os.getenv(name) for name in required)


def detect_modality(file_name: str, content_type: str) -> str:
    content_type = (content_type or "").lower()
    if content_type.startswith("image/"):
        return "image"
    if content_type.startswith("audio/"):
        return "audio"
    if content_type.startswith("video/"):
        return "video"

    ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    if ext in IMAGE_EXTS:
        return "image"
    if ext in AUDIO_EXTS:
        return "audio"
    if ext in VIDEO_EXTS:
        return "video"
    return "document"


def select_analyzer(modality: str) -> str:
    # Para documentos respetamos un analyzer personalizado si existe;
    # en caso contrario usamos el predefinido (OCR Read).
    if modality == "document":
        custom = os.getenv("AZURE_CONTENT_UNDERSTANDING_ANALYZER_ID")
        if custom:
            return custom
    env_var = ANALYZER_ENV_VARS.get(modality)
    if env_var and os.getenv(env_var):
        return os.environ[env_var]
    return DEFAULT_ANALYZERS.get(modality, "prebuilt-read")


def analyze_with_demo(modality: str, file_name: str, file_bytes: bytes) -> dict[str, Any]:
    if modality == "audio":
        markdown = (
            "[00:00] Agente: Gracias por llamar a Contoso, le atiende Ana.\n"
            "[00:05] Cliente: Hola, tengo una duda sobre mi factura de este mes.\n"
            "[00:12] Agente: Claro, reviso su cuenta ahora mismo.\n\n"
            "Resumen: el cliente consulta un cargo en su factura mensual."
        )
        return {"mode": "demo", "fileName": file_name, "result": {"contents": [{"markdown": markdown, "kind": "audio"}]}}

    if modality == "video":
        markdown = (
            "Escena 1 [00:00-00:08]: Plano de apertura con el logotipo de Contoso.\n"
            "Escena 2 [00:08-00:25]: Una presentadora explica el nuevo servicio.\n\n"
            "Transcripcion: Bienvenidos a la demostracion del producto..."
        )
        return {"mode": "demo", "fileName": file_name, "result": {"contents": [{"markdown": markdown, "kind": "video"}]}}

    # Documento o imagen -> simulamos texto extraido por OCR Read.
    text = file_bytes.decode("utf-8", errors="ignore").strip()
    if not text or modality == "image":
        text = (
            "CONTOSO LTD.\n\n# FORMULARIO DE CONTACTO\n\n"
            "Nombre: Ana Lopez\nEmpresa: Contoso Marketing\nCorreo: ana@contoso.com\n"
            "Telefono: 555-123-4567\nServicio solicitado: Campana de redes sociales\n"
            "Presupuesto estimado: $15,000\nFecha: 12/06/2026\n"
            "Comentarios: Texto simulado por OCR para la clase."
        )

    return {
        "mode": "demo",
        "fileName": file_name,
        "result": {"contents": [{"markdown": text, "kind": "document"}]},
    }


def find_markdown(payload: Any) -> str:
    parts: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            md = node.get("markdown")
            if isinstance(md, str) and md.strip():
                parts.append(md.strip())
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    return "\n\n".join(dict.fromkeys(parts))


def analyze_with_azure(
    file_name: str,
    file_bytes: bytes,
    content_type: str,
    analyzer_id: str,
    max_attempts: int = 60,
) -> dict[str, Any]:
    endpoint = os.environ["AZURE_CONTENT_UNDERSTANDING_ENDPOINT"].rstrip("/")
    api_key = os.environ["AZURE_CONTENT_UNDERSTANDING_KEY"]
    api_version = os.getenv("AZURE_CONTENT_UNDERSTANDING_API_VERSION", "2025-11-01")

    analyze_url = (
        f"{endpoint}/contentunderstanding/analyzers/{analyzer_id}:analyze"
        f"?api-version={api_version}"
    )
    headers = {
        "Ocp-Apim-Subscription-Key": api_key,
        "Content-Type": "application/json",
    }
    body = {
        "inputs": [
            {
                "name": file_name,
                "mimeType": content_type or "application/octet-stream",
                "data": base64.b64encode(file_bytes).decode("utf-8"),
            }
        ]
    }

    response = requests.post(analyze_url, headers=headers, json=body, timeout=120)
    response.raise_for_status()

    operation_location = response.headers.get("operation-location") or response.headers.get("Operation-Location")
    if not operation_location:
        return response.json()

    poll_headers = {"Ocp-Apim-Subscription-Key": api_key}
    for _ in range(max_attempts):
        poll_response = requests.get(operation_location, headers=poll_headers, timeout=30)
        poll_response.raise_for_status()
        payload = poll_response.json()
        status = str(payload.get("status", "")).lower()

        if status in {"succeeded", "failed", "canceled"}:
            if status != "succeeded":
                raise RuntimeError(f"Azure regreso estado '{status}'. Revisa el analyzer o el archivo.")
            return payload

        time.sleep(2)

    raise TimeoutError("Azure tardo demasiado en responder. Intenta con un archivo mas pequeno.")


def find_fields(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        if isinstance(payload.get("fields"), dict):
            return payload["fields"]

        result = payload.get("result")
        if isinstance(result, dict):
            contents = result.get("contents")
            if isinstance(contents, list) and contents:
                first_content = contents[0]
                if isinstance(first_content, dict) and isinstance(first_content.get("fields"), dict):
                    return first_content["fields"]

            analyzer_result = result.get("analyzerResult")
            if isinstance(analyzer_result, dict):
                fields = find_fields(analyzer_result)
                if fields:
                    return fields

        for value in payload.values():
            fields = find_fields(value)
            if fields:
                return fields

    if isinstance(payload, list):
        for item in payload:
            fields = find_fields(item)
            if fields:
                return fields

    return {}


def field_value(field: Any) -> str:
    if isinstance(field, dict):
        for key in ["valueString", "valueDate", "valueTime", "valueNumber", "valueInteger", "valueBoolean", "value", "content", "text"]:
            if field.get(key) is not None:
                return str(field[key])
        if "valueObject" in field:
            return ", ".join(
                f"{key}: {field_value(value)}"
                for key, value in field["valueObject"].items()
            )
        if "valueArray" in field:
            return "; ".join(field_value(item) for item in field["valueArray"])
    return str(field)


def field_confidence(field: Any) -> str:
    if isinstance(field, dict) and field.get("confidence") is not None:
        return f"{float(field['confidence']):.0%}"
    return ""


def fields_to_dataframe(fields: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for key, field in fields.items():
        label = FIELD_LABELS.get(key, key.replace("_", " ").title())
        rows.append(
            {
                "Campo": label,
                "Valor": field_value(field),
                "Confianza": field_confidence(field),
            }
        )
    return pd.DataFrame(rows)


st.set_page_config(page_title="Extractor de formularios", layout="wide")

st.markdown(
    """
    <style>
    /* Ocultar barra superior, menu, footer y decoraciones de Streamlit */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stHeader"] {display: none;}
    [data-testid="stToolbar"] {display: none;}
    [data-testid="stDecoration"] {display: none;}
    [data-testid="stStatusWidget"] {display: none;}

    /* Ocultar por completo la barra lateral y su control de despliegue */
    [data-testid="stSidebar"] {display: none;}
    [data-testid="stSidebarCollapsedControl"] {display: none;}
    [data-testid="collapsedControl"] {display: none;}

    /* Centrar el contenido principal con un ancho maximo comodo */
    .block-container {
        max-width: 880px;
        margin-left: auto;
        margin-right: auto;
        padding-top: 2.5rem;
        padding-bottom: 3rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# La configuracion de Azure se resuelve solo por variables de entorno.
# Si hay credenciales se usa Azure; en caso contrario se usa el modo demo.
azure_ready = has_azure_config()
use_demo = not azure_ready

st.title("Extractor de formularios")
st.caption("Extrae informacion de documentos e imagenes (OCR Read), audio y video de forma automatica.")

uploaded_file = st.file_uploader(
    "Sube un documento, imagen, audio o video",
    type=[
        "pdf", "txt", "docx", "doc", "rtf", "html", "md",
        "png", "jpg", "jpeg", "bmp", "tif", "tiff", "gif", "webp",
        "mp3", "wav", "m4a", "aac", "ogg", "flac",
        "mp4", "mov", "avi", "mkv", "webm", "m4v",
    ],
)

if uploaded_file:
    modality = detect_modality(uploaded_file.name, uploaded_file.type)
    file_bytes = uploaded_file.getvalue()

    st.write(f"Archivo seleccionado: `{uploaded_file.name}`  -  **{MODALITY_LABELS.get(modality, modality)}**")

    if modality == "image":
        st.image(uploaded_file, use_container_width=True)
    elif modality == "audio":
        st.audio(file_bytes)
    elif modality == "video":
        st.video(file_bytes)
    elif uploaded_file.type == "text/plain":
        st.text_area("Vista previa", file_bytes.decode("utf-8", errors="ignore"), height=220)
    else:
        st.info("Vista previa no disponible para este tipo de archivo, pero puedes analizarlo.")

    if st.button("Extraer informacion", type="primary"):
        # Audio y video tardan mas en procesarse: ampliamos los intentos de sondeo.
        max_attempts = 180 if modality in {"audio", "video"} else 60
        spinner_msg = {
            "audio": "Transcribiendo audio...",
            "video": "Analizando video...",
        }.get(modality, "Extrayendo texto...")

        try:
            with st.spinner(spinner_msg):
                if use_demo:
                    payload = analyze_with_demo(modality, uploaded_file.name, file_bytes)
                else:
                    analyzer_id = select_analyzer(modality)
                    payload = analyze_with_azure(
                        uploaded_file.name,
                        file_bytes,
                        uploaded_file.type,
                        analyzer_id,
                        max_attempts=max_attempts,
                    )

            st.subheader("Resultado")

            fields = find_fields(payload)
            text = find_markdown(payload)

            if fields:
                df = fields_to_dataframe(fields)
                st.dataframe(df, use_container_width=True, hide_index=True)

                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "Descargar CSV",
                    data=csv,
                    file_name="datos_extraidos.csv",
                    mime="text/csv",
                )

            if text:
                result_label = "Transcripcion" if modality in {"audio", "video"} else "Texto extraido (OCR Read)"
                st.markdown(f"**{result_label}**")
                st.text_area("Contenido", text, height=320, label_visibility="collapsed")
                st.download_button(
                    "Descargar texto",
                    data=text.encode("utf-8"),
                    file_name="contenido_extraido.txt",
                    mime="text/plain",
                )

            if not fields and not text:
                st.warning("No encontre contenido estructurado ni texto en la respuesta.")

            with st.expander("Ver JSON completo"):
                st.json(payload)

        except Exception as exc:
            st.error("No se pudo analizar el archivo.")
            st.exception(exc)
else:
    st.info("Para empezar, sube un documento, imagen, audio o video.")
