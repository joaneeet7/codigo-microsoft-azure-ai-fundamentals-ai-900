import base64
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests
from azure.core.exceptions import ResourceExistsError
from azure.storage.blob import BlobSasPermissions, BlobServiceClient, ContentSettings, generate_blob_sas
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env", override=True, encoding="utf-8-sig")

CU_ENDPOINT = os.getenv("CONTENT_UNDERSTANDING_ENDPOINT", "").strip().rstrip("/")
CU_KEY = os.getenv("CONTENT_UNDERSTANDING_KEY", "").strip()
CU_API_VERSION = os.getenv("CONTENT_UNDERSTANDING_API_VERSION", "2025-11-01").strip()
ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN", "http://localhost:5180")
CU_POLL_ATTEMPTS = int(os.getenv("CONTENT_UNDERSTANDING_POLL_ATTEMPTS", "120"))
CU_POLL_INTERVAL_SECONDS = float(os.getenv("CONTENT_UNDERSTANDING_POLL_INTERVAL_SECONDS", "2"))
CU_INPUT_MODE = os.getenv("CONTENT_UNDERSTANDING_INPUT_MODE", "blob").strip().lower()
STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "").strip()
STORAGE_CONTAINER = os.getenv("AZURE_STORAGE_CONTAINER", "content-understanding-inputs").strip()

MAX_FILE_BYTES = 25 * 1024 * 1024
SUPPORTED_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/tiff",
    "text/plain",
}
DEFAULT_ANALYZERS = ["prebuilt-invoice", "prebuilt-documentSearch", "prebuilt-imageSearch", "prebuilt-tax.us.w2", "prebuilt-tax.us.w4", "prebuilt-tax.us.1099NEC"]

app = FastAPI(title="Content Understanding API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN, "http://127.0.0.1:5180"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/api/config")
def config() -> dict[str, Any]:
    return {
        "configured": has_config(),
        "apiVersion": CU_API_VERSION,
        "analyzers": DEFAULT_ANALYZERS,
        "inputMode": "blob" if should_use_blob_input() else "data",
        "storageConfigured": bool(STORAGE_CONNECTION_STRING),
    }


@app.post("/api/analyze")
async def analyze_document(
    analyzer_id: str = Form("prebuilt-invoice"),
    file: UploadFile = File(...),
) -> dict[str, Any]:
    file_bytes = await file.read()
    validate_file(file, file_bytes)
    analyzer = analyzer_id.strip() or "prebuilt-invoice"

    if has_config():
        return analyze_with_azure(analyzer, file, file_bytes)

    return analyze_locally(analyzer, file, file_bytes)


def has_config() -> bool:
    has_azure = bool(CU_ENDPOINT and CU_KEY)
    has_required_input = CU_INPUT_MODE != "blob" or bool(STORAGE_CONNECTION_STRING)
    return has_azure and has_required_input


def should_use_blob_input() -> bool:
    return CU_INPUT_MODE == "blob" and bool(STORAGE_CONNECTION_STRING)


def validate_file(file: UploadFile, file_bytes: bytes) -> None:
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Sube un archivo valido.")
    if len(file_bytes) > MAX_FILE_BYTES:
        raise HTTPException(status_code=400, detail="El archivo supera el limite de 25 MB.")
    if file.content_type not in SUPPORTED_TYPES:
        raise HTTPException(status_code=400, detail="Formato no soportado. Usa PDF, imagen o TXT.")


def content_understanding_endpoint() -> str:
    if CU_ENDPOINT.endswith(".services.ai.azure.com"):
        return CU_ENDPOINT
    return CU_ENDPOINT.replace(".cognitiveservices.azure.com", ".services.ai.azure.com")


def analyze_with_azure(analyzer_id: str, file: UploadFile, file_bytes: bytes) -> dict[str, Any]:
    url = f"{content_understanding_endpoint()}/contentunderstanding/analyzers/{analyzer_id}:analyze"
    payload: dict[str, Any] = {
        "inputs": [build_azure_input(file, file_bytes)]
    }
    response = requests.post(
        url,
        params={"api-version": CU_API_VERSION, "stringEncoding": "utf8"},
        headers={
            "Ocp-Apim-Subscription-Key": CU_KEY,
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=120,
    )

    if response.status_code != 202:
        raise_azure_error(response)

    operation_url = response.headers.get("Operation-Location")
    if not operation_url:
        raise HTTPException(status_code=502, detail="Azure no devolvio Operation-Location.")

    result = poll_result(operation_url)
    return {
        "mode": "azure",
        "analyzerId": analyzer_id,
        "fileName": file.filename,
        "contentType": file.content_type,
        "bytes": len(file_bytes),
        "summary": summarize_result(result),
        "raw": result,
    }



def build_azure_input(file: UploadFile, file_bytes: bytes) -> dict[str, str]:
    if should_use_blob_input():
        return {"url": upload_input_to_blob(file, file_bytes)}

    encoded = base64.b64encode(file_bytes).decode("utf-8")
    return {
        "name": file.filename or "input",
        "mimeType": file.content_type or "application/octet-stream",
        "data": encoded,
    }


def upload_input_to_blob(file: UploadFile, file_bytes: bytes) -> str:
    connection = parse_storage_connection_string(STORAGE_CONNECTION_STRING)
    if "AccountName" not in connection or "AccountKey" not in connection:
        raise HTTPException(
            status_code=500,
            detail="AZURE_STORAGE_CONNECTION_STRING debe incluir AccountName y AccountKey.",
        )

    service = BlobServiceClient.from_connection_string(STORAGE_CONNECTION_STRING)
    container = service.get_container_client(STORAGE_CONTAINER)
    try:
        container.create_container()
    except ResourceExistsError:
        pass

    filename = safe_blob_filename(file.filename or "input")
    blob_name = f"inputs/{uuid.uuid4()}-{filename}"
    blob = container.get_blob_client(blob_name)
    blob.upload_blob(
        file_bytes,
        overwrite=True,
        content_settings=ContentSettings(content_type=file.content_type or "application/octet-stream"),
    )

    sas = generate_blob_sas(
        account_name=connection["AccountName"],
        container_name=STORAGE_CONTAINER,
        blob_name=blob_name,
        account_key=connection["AccountKey"],
        permission=BlobSasPermissions(read=True),
        expiry=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    return f"{blob.url}?{sas}"


def parse_storage_connection_string(connection_string: str) -> dict[str, str]:
    pairs = {}
    for segment in connection_string.split(";"):
        if "=" in segment:
            key, value = segment.split("=", 1)
            pairs[key] = value
    return pairs


def safe_blob_filename(filename: str) -> str:
    cleaned = "".join(char if char.isalnum() or char in {".", "-", "_"} else "-" for char in filename)
    return cleaned[:120] or "input"

def poll_result(operation_url: str) -> dict[str, Any]:
    headers = {"Ocp-Apim-Subscription-Key": CU_KEY}
    last_status = "NotStarted"
    for _ in range(CU_POLL_ATTEMPTS):
        response = requests.get(operation_url, headers=headers, timeout=60)
        if not response.ok:
            raise_azure_error(response)
        data = response.json()
        status = str(data.get("status") or data.get("state") or "").lower()
        last_status = status or last_status
        if status in {"succeeded", "completed", "success"}:
            return data
        if status in {"failed", "error", "canceled", "cancelled"}:
            raise HTTPException(status_code=502, detail=format_azure_error(data.get("error", {})))
        time.sleep(CU_POLL_INTERVAL_SECONDS)
    raise HTTPException(status_code=504, detail=f"Azure sigue procesando el documento despues de {CU_POLL_ATTEMPTS * CU_POLL_INTERVAL_SECONDS:.0f} segundos. Ultimo estado: {last_status}.")


def summarize_result(data: dict[str, Any]) -> dict[str, Any]:
    result = data.get("result", {})
    contents = result.get("contents", []) or []
    first = contents[0] if contents else {}
    fields = first.get("fields", {}) or {}
    field_rows = flatten_fields(fields)[:24]
    markdown = first.get("markdown", "")
    pages = first.get("pages", []) or []
    tables = first.get("tables", []) or []
    key_values = first.get("keyValuePairs", []) or []

    return {
        "status": data.get("status"),
        "markdown": markdown[:6000],
        "fields": field_rows,
        "pageCount": len(pages),
        "tableCount": len(tables),
        "keyValueCount": len(key_values),
        "usage": data.get("usage", {}),
    }


def flatten_fields(fields: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for name, value in fields.items():
        rows.append({
            "name": name,
            "type": value.get("type"),
            "value": extract_field_value(value),
            "confidence": value.get("confidence"),
        })
    return rows


def extract_field_value(field: dict[str, Any]) -> Any:
    for key in ("valueString", "valueNumber", "valueInteger", "valueDate", "valueTime", "valueBoolean"):
        if key in field:
            return field[key]
    if "valueObject" in field:
        return {name: extract_field_value(value) for name, value in field["valueObject"].items()}
    if "valueArray" in field:
        return [extract_field_value(item) for item in field["valueArray"]]
    return None


def format_azure_error(error: Any) -> str:
    if not isinstance(error, dict):
        return "El analisis fallo en Azure."

    parts = []
    code = error.get("code")
    message = error.get("message")
    target = error.get("target")
    inner = error.get("innererror") or error.get("innerError")
    details = error.get("details")

    if message:
        parts.append(str(message))
    if code:
        parts.append(f"Codigo: {code}")
    if target:
        parts.append(f"Target: {target}")
    if isinstance(inner, dict):
        inner_code = inner.get("code")
        inner_message = inner.get("message")
        if inner_message:
            parts.append(f"Inner: {inner_message}")
        elif inner_code:
            parts.append(f"Inner code: {inner_code}")
    if isinstance(details, list) and details:
        detail_messages = []
        for item in details[:3]:
            if isinstance(item, dict):
                detail_messages.append(item.get("message") or item.get("code") or str(item))
            else:
                detail_messages.append(str(item))
        parts.append("Detalles: " + " | ".join(str(item) for item in detail_messages if item))

    return " ".join(parts) or "El analisis fallo en Azure."


def raise_azure_error(response: requests.Response) -> None:
    try:
        data = response.json()
    except ValueError:
        data = {}
    error = data.get("error", {}) if isinstance(data, dict) else {}
    detail = format_azure_error(error)
    raise HTTPException(status_code=response.status_code, detail=detail or "Error al llamar Azure Content Understanding.")


def analyze_locally(analyzer_id: str, file: UploadFile, file_bytes: bytes) -> dict[str, Any]:
    kb = max(1, round(len(file_bytes) / 1024))
    return {
        "mode": "demo",
        "analyzerId": analyzer_id,
        "fileName": file.filename,
        "contentType": file.content_type,
        "bytes": len(file_bytes),
        "summary": {
            "status": "Demo",
            "markdown": f"# Modo demo local\n\nArchivo recibido: {file.filename or 'sin nombre'} ({kb} KB). Configura Azure para extraer campos reales.",
            "fields": [
                {"name": "Archivo", "type": "string", "value": file.filename or "sin nombre", "confidence": 1},
                {"name": "Analyzer", "type": "string", "value": analyzer_id, "confidence": 1},
            ],
            "pageCount": 0,
            "tableCount": 0,
            "keyValueCount": 0,
            "usage": {},
        },
        "raw": {"message": "Configura CONTENT_UNDERSTANDING_ENDPOINT y CONTENT_UNDERSTANDING_KEY."},
    }