import base64
import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env", override=True, encoding="utf-8-sig")

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip().rstrip("/")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "").strip()
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o-mini").strip()
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21").strip()
ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN", "http://localhost:5178")
AZURE_IMAGE_DETAIL = os.getenv("AZURE_IMAGE_DETAIL", "low").strip().lower()

MAX_IMAGE_BYTES = 20 * 1024 * 1024
SUPPORTED_TYPES = {"image/png", "image/jpeg", "image/webp"}

app = FastAPI(title="Visual Input Multimodal API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN, "http://127.0.0.1:5178"],
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
        "configured": has_azure_config(),
        "deployment": AZURE_OPENAI_DEPLOYMENT_NAME,
        "apiVersion": AZURE_OPENAI_API_VERSION,
        "supportedTypes": sorted(SUPPORTED_TYPES),
    }


@app.post("/api/analyze-visual")
async def analyze_visual(
    prompt: str = Form(..., min_length=3, max_length=4000),
    image: UploadFile = File(...),
) -> dict[str, Any]:
    image_bytes = await image.read()
    validate_image(image, image_bytes)

    if has_azure_config():
        return analyze_with_azure(prompt.strip(), image, image_bytes)

    return analyze_locally(prompt.strip(), image, image_bytes)


def has_azure_config() -> bool:
    return bool(AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY and AZURE_OPENAI_DEPLOYMENT_NAME)


def validate_image(image: UploadFile, image_bytes: bytes) -> None:
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Sube una imagen valida.")
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail="La imagen supera el limite de 20 MB.")
    if image.content_type not in SUPPORTED_TYPES:
        raise HTTPException(status_code=400, detail="Formato no soportado. Usa PNG, JPG o WEBP.")


def analyze_with_azure(prompt: str, image: UploadFile, image_bytes: bytes) -> dict[str, Any]:
    image_data = base64.b64encode(image_bytes).decode("utf-8")
    data_url = f"{image.content_type};base64,{image_data}"
    url = (
        f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/"
        f"{AZURE_OPENAI_DEPLOYMENT_NAME}/chat/completions"
        f"?api-version={AZURE_OPENAI_API_VERSION}"
    )

    response = requests.post(
        url,
        headers={
            "api-key": AZURE_OPENAI_API_KEY,
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
                        {"type": "image_url", "image_url": {"url": f"data:{data_url}", "detail": AZURE_IMAGE_DETAIL if AZURE_IMAGE_DETAIL in {"low", "high", "auto"} else "low"}},
                    ],
                },
            ],
            "max_tokens": 700,
            "temperature": 0.35,
        },
        timeout=120,
    )

    try:
        data = response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="Azure devolvio una respuesta no JSON.") from exc

    if not response.ok:
        raise_azure_error(response, data)

    answer = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not answer:
        raise HTTPException(status_code=502, detail="Azure no devolvio una interpretacion.")

    return {
        "mode": "azure",
        "analysis": answer,
        "fileName": image.filename,
        "contentType": image.content_type,
        "bytes": len(image_bytes),
        "deployment": AZURE_OPENAI_DEPLOYMENT_NAME,
    }


def raise_azure_error(response: requests.Response, data: dict[str, Any]) -> None:
    error = data.get("error", {}) if isinstance(data, dict) else {}
    code = error.get("code") if isinstance(error, dict) else None
    message = error.get("message") if isinstance(error, dict) else None
    retry_after = response.headers.get("retry-after") or response.headers.get("Retry-After")

    detail_parts = []
    if message:
        detail_parts.append(message)
    elif code:
        detail_parts.append(str(code))
    else:
        detail_parts.append("No se pudo interpretar la imagen.")

    if retry_after:
        detail_parts.append(f"Intenta de nuevo en {retry_after} segundos.")

    raise HTTPException(status_code=response.status_code, detail=" ".join(detail_parts))


def analyze_locally(prompt: str, image: UploadFile, image_bytes: bytes) -> dict[str, Any]:
    kb = max(1, round(len(image_bytes) / 1024))
    answer = (
        "Modo demo local: el backend recibio la imagen y el prompt correctamente.\n\n"
        f"Archivo: {image.filename or 'sin nombre'} ({image.content_type}, {kb} KB).\n\n"
        "Cuando configures Azure OpenAI con un deployment multimodal, esta misma pantalla devolvera una interpretacion real de la imagen. "
        "Prompt recibido:\n"
        f"{prompt}"
    )

    return {
        "mode": "demo",
        "analysis": answer,
        "fileName": image.filename,
        "contentType": image.content_type,
        "bytes": len(image_bytes),
        "deployment": "demo-local",
    }