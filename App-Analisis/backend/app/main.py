import os
import re
from math import ceil
from typing import Any, Literal

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

PORT = int(os.getenv("PORT", "3010"))
ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN", "http://localhost:5174")
AZURE_LANGUAGE_ENDPOINT = os.getenv("AZURE_LANGUAGE_ENDPOINT", "").strip()
AZURE_LANGUAGE_KEY = os.getenv("AZURE_LANGUAGE_KEY", "").strip()

app = FastAPI(title="App Analisis Texto API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    text: str


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.post("/api/analyze")
def analyze_text(payload: AnalyzeRequest) -> dict[str, Any]:
    text = payload.text.strip()

    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    if has_azure_config():
        return analyze_with_azure(text)

    return analyze_locally(text)


def has_azure_config() -> bool:
    return bool(AZURE_LANGUAGE_ENDPOINT and AZURE_LANGUAGE_KEY)


def analyze_with_azure(text: str) -> dict[str, Any]:
    language = call_azure("LanguageDetection", [{"id": "1", "text": text}])
    sentiment = call_azure("SentimentAnalysis", [{"id": "1", "text": text, "language": "es"}])
    key_phrases = call_azure("KeyPhraseExtraction", [{"id": "1", "text": text, "language": "es"}])
    entities = call_azure("EntityRecognition", [{"id": "1", "text": text, "language": "es"}])

    return {
        "mode": "azure",
        "language": language["detectedLanguage"],
        "sentiment": sentiment["sentiment"],
        "confidenceScores": sentiment["confidenceScores"],
        "keyPhrases": key_phrases.get("keyPhrases", []),
        "entities": entities.get("entities", []),
        "stats": get_stats(text),
    }


def call_azure(kind: str, documents: list[dict[str, str]]) -> dict[str, Any]:
    url = f"{AZURE_LANGUAGE_ENDPOINT.rstrip('/')}/language/:analyze-text?api-version=2023-04-01"
    response = requests.post(
        url,
        headers={
            "Content-Type": "application/json",
            "Ocp-Apim-Subscription-Key": AZURE_LANGUAGE_KEY,
        },
        json={
            "kind": kind,
            "parameters": {"modelVersion": "latest"},
            "analysisInput": {"documents": documents},
        },
        timeout=30,
    )

    try:
        payload = response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="Azure Language returned a non-JSON response") from exc

    if not response.ok:
        message = payload.get("error", {}).get("message", f"Azure Language request failed: {kind}")
        raise HTTPException(status_code=502, detail=message)

    result = payload.get("results", {}).get("documents", [None])[0]
    if not result:
        raise HTTPException(status_code=502, detail=f"Azure Language returned no document result for {kind}")

    return result


def analyze_locally(text: str) -> dict[str, Any]:
    positive_words = ["excelente", "bueno", "increible", "feliz", "rapido", "util", "mejor"]
    negative_words = ["malo", "lento", "error", "problema", "triste", "dificil", "difícil"]
    lower_text = text.lower()

    positive_count = sum(1 for word in positive_words if word in lower_text)
    negative_count = sum(1 for word in negative_words if word in lower_text)

    sentiment: Literal["positive", "neutral", "negative"]
    if positive_count > negative_count:
        sentiment = "positive"
    elif negative_count > positive_count:
        sentiment = "negative"
    else:
        sentiment = "neutral"

    return {
        "mode": "local",
        "language": {
            "name": "Spanish",
            "iso6391Name": "es",
            "confidenceScore": 0.72,
        },
        "sentiment": sentiment,
        "confidenceScores": {
            "positive": 0.76 if sentiment == "positive" else 0.12,
            "neutral": 0.72 if sentiment == "neutral" else 0.18,
            "negative": 0.76 if sentiment == "negative" else 0.10,
        },
        "keyPhrases": extract_local_key_phrases(text),
        "entities": extract_local_entities(text),
        "stats": get_stats(text),
    }


def extract_local_key_phrases(text: str) -> list[str]:
    stop_words = {
        "para",
        "pero",
        "como",
        "este",
        "esta",
        "tiene",
        "con",
        "los",
        "las",
        "una",
        "del",
        "que",
        "por",
    }
    clean_text = re.sub(r"[^\w\sáéíóúñÁÉÍÓÚÑ]", " ", text.lower(), flags=re.UNICODE)
    words = [word for word in clean_text.split() if len(word) > 4 and word not in stop_words]

    unique_words: list[str] = []
    for word in words:
        if word not in unique_words:
            unique_words.append(word)

    return unique_words[:8]


def extract_local_entities(text: str) -> list[dict[str, Any]]:
    matches = re.findall(r"\b[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ0-9-]{2,}\b", text, flags=re.UNICODE)
    unique_matches: list[str] = []

    for item in matches:
        if item not in unique_matches:
            unique_matches.append(item)

    return [
        {
            "text": item,
            "category": "Entidad posible",
            "confidenceScore": 0.58,
        }
        for item in unique_matches[:8]
    ]


def get_stats(text: str) -> dict[str, int]:
    words = [word for word in text.strip().split() if word]
    sentences = [sentence for sentence in re.split(r"[.!?]+", text) if sentence.strip()]

    return {
        "characters": len(text),
        "words": len(words),
        "sentences": len(sentences),
        "readingTimeMinutes": max(1, ceil(len(words) / 180)),
    }
