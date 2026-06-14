import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env", override=True, encoding="utf-8-sig")

VISION_ENDPOINT = os.getenv("VISION_ENDPOINT", "").strip().rstrip("/")
VISION_KEY = os.getenv("VISION_KEY", "").strip()
VISION_API_VERSION = os.getenv("VISION_API_VERSION", "2024-02-01").strip()
ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN", "http://localhost:5179")

MAX_IMAGE_BYTES = 20 * 1024 * 1024
SUPPORTED_TYPES = {"image/png", "image/jpeg", "image/webp", "image/bmp", "image/gif"}
DEFAULT_FEATURES = ["caption", "denseCaptions", "tags", "objects", "read", "people", "smartCrops"]
SUPPORTED_FEATURES = set(DEFAULT_FEATURES)

app = FastAPI(title="App Vision API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN, "http://127.0.0.1:5179"],
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
        "configured": has_vision_config(),
        "apiVersion": VISION_API_VERSION,
        "features": DEFAULT_FEATURES,
    }


@app.post("/api/analyze")
async def analyze(
    features: str = Form(",".join(DEFAULT_FEATURES)),
    image: UploadFile = File(...),
) -> dict[str, Any]:
    image_bytes = await image.read()
    validate_image(image, image_bytes)
    selected_features = parse_features(features)

    if has_vision_config():
        return analyze_with_azure(image, image_bytes, selected_features)

    return analyze_locally(image, image_bytes, selected_features)


def has_vision_config() -> bool:
    return bool(VISION_ENDPOINT and VISION_KEY)


def validate_image(image: UploadFile, image_bytes: bytes) -> None:
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Sube una imagen valida.")
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail="La imagen supera el limite de 20 MB.")
    if image.content_type not in SUPPORTED_TYPES:
        raise HTTPException(status_code=400, detail="Formato no soportado. Usa PNG, JPG, WEBP, BMP o GIF.")


def parse_features(features: str) -> list[str]:
    selected = [item.strip() for item in features.split(",") if item.strip()]
    invalid = [item for item in selected if item not in SUPPORTED_FEATURES]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Features no soportadas: {', '.join(invalid)}")
    return selected or DEFAULT_FEATURES


def analyze_with_azure(image: UploadFile, image_bytes: bytes, features: list[str]) -> dict[str, Any]:
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
            "Content-Type": image.content_type or "application/octet-stream",
        },
        data=image_bytes,
        timeout=120,
    )

    try:
        data = response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="Azure devolvio una respuesta no JSON.") from exc

    if not response.ok:
        error = data.get("error", {}) if isinstance(data, dict) else {}
        message = error.get("message") if isinstance(error, dict) else None
        code = error.get("code") if isinstance(error, dict) else None
        header_code = response.headers.get("x-ms-error-code")
        detail = message or code or header_code or "No se pudo analizar la imagen."
        if header_code and header_code not in detail:
            detail = f"{detail} ({header_code})"
        raise HTTPException(status_code=response.status_code, detail=detail)

    return {
        "mode": "azure",
        "fileName": image.filename,
        "contentType": image.content_type,
        "bytes": len(image_bytes),
        "features": features,
        "summary": summarize_result(data),
        "raw": data,
    }


def summarize_result(data: dict[str, Any]) -> dict[str, Any]:
    caption = data.get("captionResult", {}).get("text")
    tags = [item.get("name") for item in data.get("tagsResult", {}).get("values", [])[:10] if item.get("name")]
    objects = [item.get("tags", [{}])[0].get("name") for item in data.get("objectsResult", {}).get("values", [])[:8]]
    people = len(data.get("peopleResult", {}).get("values", []) or [])
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


def analyze_locally(image: UploadFile, image_bytes: bytes, features: list[str]) -> dict[str, Any]:
    kb = max(1, round(len(image_bytes) / 1024))
    summary = {
        "caption": "Modo demo local: imagen recibida correctamente.",
        "tags": ["demo", "vision", "imagen"],
        "objects": [],
        "people": 0,
        "denseCaptions": [f"Archivo {image.filename or 'sin nombre'} listo para analizar con Azure AI Vision."],
        "readLines": [],
    }

    return {
        "mode": "demo",
        "fileName": image.filename,
        "contentType": image.content_type,
        "bytes": len(image_bytes),
        "features": features,
        "summary": summary,
        "raw": {
            "message": "Configura VISION_ENDPOINT y VISION_KEY para usar Azure AI Vision.",
            "fileSizeKb": kb,
        },
    }