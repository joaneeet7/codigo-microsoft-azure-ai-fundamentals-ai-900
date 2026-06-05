import base64
import os
import tempfile
from pathlib import Path
from typing import Any, Optional, Union

import azure.cognitiveservices.speech as speechsdk
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env", override=True)

SPEECH_KEY = os.getenv("SPEECH_KEY", "").strip()
SPEECH_REGION = os.getenv("SPEECH_REGION", "").strip()
DEFAULT_VOICE = os.getenv("SPEECH_VOICE_NAME", "es-MX-DaliaNeural").strip()
DEFAULT_RECOGNITION_LANGUAGE = os.getenv("SPEECH_RECOGNITION_LANGUAGE", "es-MX").strip()
ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN", "http://localhost:5175")

app = FastAPI(title="Azure Speech Demo API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SynthesizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)
    voiceName: Optional[str] = None


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/api/speech/config")
def speech_config() -> dict[str, Any]:
    return {
        "configured": has_speech_config(),
        "region": SPEECH_REGION or None,
        "defaultVoice": DEFAULT_VOICE,
        "recognitionLanguage": DEFAULT_RECOGNITION_LANGUAGE,
    }


@app.post("/api/speech/synthesize")
def synthesize(payload: SynthesizeRequest) -> dict[str, Any]:
    require_speech_config()

    text = payload.text.strip()
    voice_name = payload.voiceName or DEFAULT_VOICE

    speech_config = build_speech_config()
    speech_config.speech_synthesis_voice_name = voice_name
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
    )

    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config,
        audio_config=None,
    )
    result = synthesizer.speak_text_async(text).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return {
            "mode": "azure",
            "voiceName": voice_name,
            "contentType": "audio/mpeg",
            "audioBase64": base64.b64encode(result.audio_data).decode("utf-8"),
            "characters": len(text),
        }

    detail = get_cancellation_detail(result)
    raise HTTPException(status_code=502, detail=detail)


@app.post("/api/speech/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    language: str = Form(DEFAULT_RECOGNITION_LANGUAGE),
) -> dict[str, Any]:
    require_speech_config()

    suffix = (Path(file.filename or "audio.wav").suffix or ".wav").lower()
    if suffix != ".wav":
        raise HTTPException(status_code=400, detail="Sube un archivo WAV para transcripcion.")

    temp_path = ""
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_path = temp_file.name
        temp_file.write(await file.read())

    try:
        speech_config = build_speech_config()
        speech_config.speech_recognition_language = language or DEFAULT_RECOGNITION_LANGUAGE
        audio_config = speechsdk.audio.AudioConfig(filename=temp_path)
        try:
            recognizer = speechsdk.SpeechRecognizer(
                speech_config=speech_config,
                audio_config=audio_config,
            )
            result = recognizer.recognize_once_async().get()
        except RuntimeError as exc:
            raise HTTPException(
                status_code=400,
                detail=(
                    "No se pudo leer el audio. Sube un WAV PCM sin comprimir "
                    "(mono, 16 kHz, 16-bit). Convierte el archivo si viene de MP3, "
                    "M4A u otro formato."
                ),
            ) from exc

        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            return {
                "mode": "azure",
                "language": speech_config.speech_recognition_language,
                "text": result.text,
            }

        if result.reason == speechsdk.ResultReason.NoMatch:
            return {
                "mode": "azure",
                "language": speech_config.speech_recognition_language,
                "text": "",
                "message": "No se reconocio voz en el audio.",
            }

        detail = get_cancellation_detail(result)
        raise HTTPException(status_code=502, detail=detail)
    finally:
        if temp_path:
            try:
                os.remove(temp_path)
            except OSError:
                pass

def has_speech_config() -> bool:
    return bool(SPEECH_KEY and SPEECH_REGION)


def require_speech_config() -> None:
    if not has_speech_config():
        raise HTTPException(
            status_code=503,
            detail="Configura SPEECH_KEY y SPEECH_REGION en backend/.env para usar Azure Speech.",
        )


def build_speech_config() -> speechsdk.SpeechConfig:
    return speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)


def get_cancellation_detail(result: Union[speechsdk.SpeechSynthesisResult, speechsdk.SpeechRecognitionResult]) -> str:
    cancellation = speechsdk.CancellationDetails(result)
    if cancellation.error_details:
        return cancellation.error_details
    return f"Speech request canceled: {cancellation.reason}"
