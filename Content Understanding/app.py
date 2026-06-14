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


def has_azure_config() -> bool:
    required = [
        "AZURE_CONTENT_UNDERSTANDING_ENDPOINT",
        "AZURE_CONTENT_UNDERSTANDING_KEY",
        "AZURE_CONTENT_UNDERSTANDING_ANALYZER_ID",
    ]
    return all(os.getenv(name) for name in required)


def extract_value_from_text(text: str, label: str) -> str:
    for line in text.splitlines():
        if line.lower().startswith(label.lower() + ":"):
            return line.split(":", 1)[1].strip()
    return ""


def analyze_with_demo(file_name: str, file_bytes: bytes) -> dict[str, Any]:
    text = file_bytes.decode("utf-8", errors="ignore")

    values = {
        "nombre": extract_value_from_text(text, "Nombre") or "Ana Lopez",
        "empresa": extract_value_from_text(text, "Empresa") or "Contoso Marketing",
        "correo": extract_value_from_text(text, "Correo") or "ana@contoso.com",
        "telefono": extract_value_from_text(text, "Telefono") or "555-123-4567",
        "servicio_solicitado": extract_value_from_text(text, "Servicio solicitado") or "Campana de redes sociales",
        "presupuesto_estimado": extract_value_from_text(text, "Presupuesto estimado") or "$15,000",
        "fecha": extract_value_from_text(text, "Fecha") or "12/06/2026",
        "comentarios": extract_value_from_text(text, "Comentarios") or "Datos simulados para clase.",
    }

    return {
        "mode": "demo",
        "fileName": file_name,
        "fields": {key: {"value": value, "confidence": 0.99} for key, value in values.items()},
    }


def analyze_with_azure(file_name: str, file_bytes: bytes, content_type: str) -> dict[str, Any]:
    endpoint = os.environ["AZURE_CONTENT_UNDERSTANDING_ENDPOINT"].rstrip("/")
    api_key = os.environ["AZURE_CONTENT_UNDERSTANDING_KEY"]
    analyzer_id = os.environ["AZURE_CONTENT_UNDERSTANDING_ANALYZER_ID"]
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

    response = requests.post(analyze_url, headers=headers, json=body, timeout=60)
    response.raise_for_status()

    operation_location = response.headers.get("operation-location") or response.headers.get("Operation-Location")
    if not operation_location:
        return response.json()

    poll_headers = {"Ocp-Apim-Subscription-Key": api_key}
    for _ in range(30):
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
st.caption("Sube un documento y conviertelo en datos estructurados de forma automatica.")

uploaded_file = st.file_uploader(
    "Sube un formulario o documento",
    type=["pdf", "png", "jpg", "jpeg", "txt"],
)

if uploaded_file:
    st.write(f"Archivo seleccionado: `{uploaded_file.name}`")

    if uploaded_file.type.startswith("image/"):
        st.image(uploaded_file, use_container_width=True)
    elif uploaded_file.type == "text/plain":
        st.text_area("Vista previa", uploaded_file.getvalue().decode("utf-8", errors="ignore"), height=220)
    else:
        st.info("Vista previa no disponible para este tipo de archivo, pero puedes analizarlo.")

    if st.button("Extraer informacion", type="primary"):
        file_bytes = uploaded_file.getvalue()

        try:
            with st.spinner("Analizando documento..."):
                if use_demo:
                    payload = analyze_with_demo(uploaded_file.name, file_bytes)
                else:
                    if not azure_ready:
                        st.error("Faltan credenciales de Azure. Activa modo demo o completa el archivo .env.")
                        st.stop()
                    payload = analyze_with_azure(uploaded_file.name, file_bytes, uploaded_file.type)

            fields = find_fields(payload)

            if not fields:
                st.warning("No encontre campos estructurados en la respuesta.")
                with st.expander("Ver respuesta completa"):
                    st.json(payload)
                st.stop()

            df = fields_to_dataframe(fields)
            st.subheader("Resultado")
            st.dataframe(df, use_container_width=True, hide_index=True)

            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Descargar CSV",
                data=csv,
                file_name="datos_extraidos.csv",
                mime="text/csv",
            )

            with st.expander("Ver JSON completo"):
                st.json(payload)

        except Exception as exc:
            st.error("No se pudo analizar el documento.")
            st.exception(exc)
else:
    st.info("Para empezar, sube uno de los archivos de ejemplo.")
