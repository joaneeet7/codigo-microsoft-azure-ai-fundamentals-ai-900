import base64
import os
import textwrap
from html import escape
from pathlib import Path
from typing import Any, Literal

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env", override=True, encoding="utf-8-sig")

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip().rstrip("/")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "").strip()
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-image-1").strip()
AZURE_OPENAI_MODEL_NAME = os.getenv("AZURE_OPENAI_MODEL_NAME", AZURE_OPENAI_DEPLOYMENT_NAME).strip()
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview").strip()
IMAGE_PROVIDER = os.getenv("IMAGE_PROVIDER", "").strip().lower()
ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN", "http://localhost:5176")

app = FastAPI(title="Modelos Generativos API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN, "http://127.0.0.1:5176"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

ImageSize = Literal["1024x1024", "1024x1536", "1536x1024"]
ImageQuality = Literal["low", "medium", "high"]


class ImageRequest(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=4000)
    size: ImageSize = "1024x1024"
    quality: ImageQuality = "medium"


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/api/config")
def config() -> dict[str, Any]:
    return {
        "configured": has_azure_config(),
        "deployment": AZURE_OPENAI_DEPLOYMENT_NAME,
        "model": AZURE_OPENAI_MODEL_NAME,
        "apiVersion": AZURE_OPENAI_API_VERSION,
        "provider": resolved_provider(),
    }


@app.post("/api/generate-image")
def generate_image(payload: ImageRequest) -> dict[str, Any]:
    prompt = payload.prompt.strip()

    if has_azure_config():
        if resolved_provider() == "mai":
            return generate_with_mai(prompt, payload.size, payload.quality)
        return generate_with_azure_openai(prompt, payload.size, payload.quality)

    return generate_demo_image(prompt, payload.size, payload.quality)


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


def generate_with_mai(prompt: str, size: ImageSize, quality: ImageQuality) -> dict[str, Any]:
    endpoint = normalize_mai_endpoint(AZURE_OPENAI_ENDPOINT)
    width, height = mai_dimensions(size)
    url = f"{endpoint}/mai/v1/images/generations"

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

    data = parse_json_response(response)
    if not response.ok:
        raise_azure_error(response, data)

    image_src = extract_image_src(data)
    return {
        "mode": "azure",
        "image": image_src,
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

    data = parse_json_response(response)
    if not response.ok:
        raise_azure_error(response, data)

    image_src = extract_image_src(data)
    return {
        "mode": "azure",
        "image": image_src,
        "prompt": prompt,
        "size": size,
        "quality": quality,
        "deployment": AZURE_OPENAI_DEPLOYMENT_NAME,
    }


def parse_json_response(response: requests.Response) -> dict[str, Any]:
    try:
        return response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="Azure devolvio una respuesta no JSON.") from exc


def raise_azure_error(response: requests.Response, data: dict[str, Any]) -> None:
    error = data.get("error")
    if isinstance(error, dict):
        message = error.get("message") or error.get("code")
    else:
        message = data.get("message") or data.get("detail")
    raise HTTPException(status_code=response.status_code, detail=message or "No se pudo generar la imagen en Azure.")


def extract_image_src(data: dict[str, Any]) -> str:
    image = data.get("data", [{}])[0]
    b64_image = image.get("b64_json")
    image_url = image.get("url")

    if b64_image:
        return f"data:image/png;base64,{b64_image}"
    if image_url:
        return image_url
    raise HTTPException(status_code=502, detail="Azure no devolvio imagen.")


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