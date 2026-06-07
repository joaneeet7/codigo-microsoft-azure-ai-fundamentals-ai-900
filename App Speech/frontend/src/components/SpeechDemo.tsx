import { FormEvent, useEffect, useMemo, useState } from "react";
import AudioWaveform from "lucide-react/dist/esm/icons/audio-waveform.js";
import Bot from "lucide-react/dist/esm/icons/bot.js";
import FileAudio from "lucide-react/dist/esm/icons/file-audio.js";
import Loader2 from "lucide-react/dist/esm/icons/loader-2.js";
import MessageSquare from "lucide-react/dist/esm/icons/message-square.js";
import Mic2 from "lucide-react/dist/esm/icons/mic-2.js";
import Play from "lucide-react/dist/esm/icons/play.js";
import Radio from "lucide-react/dist/esm/icons/radio.js";
import Sparkles from "lucide-react/dist/esm/icons/sparkles.js";
import Upload from "lucide-react/dist/esm/icons/upload.js";

const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:3022";

const voices = [
  "es-MX-DaliaNeural",
  "es-MX-JorgeNeural",
  "en-US-AvaMultilingualNeural",
  "en-US-FableMultilingualNeural"
];

export function SpeechDemo() {
  const [text, setText] = useState(
    "Bienvenido a la demo de Azure Speech en Foundry Tools. Esta aplicación convierte texto en voz y transcribe audio mediante un backend en Python."
  );
  const [voiceName, setVoiceName] = useState(voices[0]);
  const [audioUrl, setAudioUrl] = useState("");
  const [transcript, setTranscript] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [configured, setConfigured] = useState(false);
  const [status, setStatus] = useState("Revisando configuracion...");
  const [isSynthesizing, setIsSynthesizing] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [error, setError] = useState("");

  const [multimodalConfigured, setMultimodalConfigured] = useState(false);
  const [multimodalModel, setMultimodalModel] = useState("");
  const [promptFile, setPromptFile] = useState<File | null>(null);
  const [instructions, setInstructions] = useState("");
  const [recognizedPrompt, setRecognizedPrompt] = useState("");
  const [answerText, setAnswerText] = useState("");
  const [answerAudioUrl, setAnswerAudioUrl] = useState("");
  const [isResponding, setIsResponding] = useState(false);

  const characterCount = useMemo(() => text.trim().length, [text]);

  useEffect(() => {
    async function loadConfig() {
      try {
        const response = await fetch(`${apiUrl}/api/speech/config`);
        const data = await response.json();
        setConfigured(Boolean(data.configured));
        setStatus(data.configured ? `Azure Speech listo en ${data.region}` : "Faltan SPEECH_KEY y SPEECH_REGION");
        if (data.defaultVoice) setVoiceName(data.defaultVoice);
      } catch {
        setConfigured(false);
        setStatus("Backend no disponible");
      }
    }

    async function loadMultimodalConfig() {
      try {
        const response = await fetch(`${apiUrl}/api/multimodal/config`);
        const data = await response.json();
        setMultimodalConfigured(Boolean(data.configured));
        setMultimodalModel(data.model || "");
      } catch {
        setMultimodalConfigured(false);
      }
    }

    loadConfig();
    loadMultimodalConfig();
  }, []);

  async function synthesize(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!text.trim() || isSynthesizing) return;

    setError("");
    setAudioUrl("");
    setIsSynthesizing(true);

    try {
      const response = await fetch(`${apiUrl}/api/speech/synthesize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, voiceName })
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "No se pudo generar el audio.");
      }

      setAudioUrl(`data:${data.contentType};base64,${data.audioBase64}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error inesperado.");
    } finally {
      setIsSynthesizing(false);
    }
  }

  async function transcribe() {
    if (!selectedFile || isTranscribing) return;

    setError("");
    setTranscript("");
    setIsTranscribing(true);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("language", "es-MX");

      const response = await fetch(`${apiUrl}/api/speech/transcribe`, {
        method: "POST",
        body: formData
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "No se pudo transcribir el audio.");
      }

      setTranscript(data.text || data.message || "Sin texto reconocido.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error inesperado.");
    } finally {
      setIsTranscribing(false);
    }
  }

  async function respond() {
    if (!promptFile || isResponding) return;

    setError("");
    setRecognizedPrompt("");
    setAnswerText("");
    setAnswerAudioUrl("");
    setIsResponding(true);

    try {
      const formData = new FormData();
      formData.append("file", promptFile);
      if (instructions.trim()) formData.append("instructions", instructions.trim());

      const response = await fetch(`${apiUrl}/api/multimodal/respond`, {
        method: "POST",
        body: formData
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "No se pudo obtener respuesta del modelo.");
      }

      setRecognizedPrompt(data.recognizedPrompt || "");
      setAnswerText(data.answerText || "El modelo no devolvio texto.");
      if (data.audioBase64) {
        setAnswerAudioUrl(`data:${data.contentType};base64,${data.audioBase64}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error inesperado.");
    } finally {
      setIsResponding(false);
    }
  }

  return (
    <main className="app-shell">
      <section className="workspace">
        <aside className="hero-panel">
          <div>
            <div className="brand-mark" aria-hidden="true">
              <AudioWaveform size={28} />
            </div>
            <p className="eyebrow">Azure Speech</p>
            <h1>Foundry Tools Voice Lab</h1>
            <p className="hero-copy">
              Demo ligera para convertir texto en voz y transcribir audio con Azure Speech y backend Python.
            </p>
          </div>

          <div className="status-card">
            <span className={configured ? "status-dot ready" : "status-dot"} />
            <div>
              <strong>{configured ? "Servicio conectado" : "Configuracion pendiente"}</strong>
              <p>{status}</p>
            </div>
          </div>
        </aside>

        <section className="main-panel">
          <form className="tool-card primary" onSubmit={synthesize}>
            <div className="card-title">
              <Sparkles size={20} />
              <div>
                <h2>Texto a voz</h2>
                <p>Genera audio MP3 con una voz neural de Azure Speech.</p>
              </div>
            </div>

            <textarea value={text} onChange={(event) => setText(event.target.value)} />

            <div className="control-row">
              <label>
                Voz
                <select value={voiceName} onChange={(event) => setVoiceName(event.target.value)}>
                  {voices.map((voice) => (
                    <option key={voice} value={voice}>
                      {voice}
                    </option>
                  ))}
                </select>
              </label>
              <span>{characterCount} caracteres</span>
            </div>

            <button className="primary-action" type="submit" disabled={!text.trim() || isSynthesizing}>
              {isSynthesizing ? <Loader2 className="spin" size={18} /> : <Play size={18} />}
              Generar voz
            </button>

            {audioUrl && (
              <div className="audio-result">
                <Radio size={18} />
                <audio src={audioUrl} controls />
              </div>
            )}
          </form>

          <section className="tool-card secondary">
            <div className="card-title">
              <Mic2 size={20} />
              <div>
                <h2>Audio a texto</h2>
                <p>Sube un archivo WAV corto para transcribirlo.</p>
              </div>
            </div>

            <label className="drop-zone">
              <FileAudio size={24} />
              <span>{selectedFile ? selectedFile.name : "Seleccionar archivo WAV"}</span>
              <input
                type="file"
                accept=".wav,audio/wav,audio/mpeg"
                onChange={(event) => setSelectedFile(event.target.files?.[0] || null)}
              />
            </label>

            <button className="secondary-action" type="button" onClick={transcribe} disabled={!selectedFile || isTranscribing}>
              {isTranscribing ? <Loader2 className="spin" size={18} /> : <Upload size={18} />}
              Transcribir audio
            </button>

            <div className="transcript-box">
              <strong>Transcripcion</strong>
              <p>{transcript || "El texto reconocido aparecera aqui."}</p>
            </div>
          </section>

          <section className="tool-card multimodal">
            <div className="card-title">
              <Bot size={20} />
              <div>
                <h2>Prompt hablado con modelo desplegado</h2>
                <p>
                  Transcribe tu audio con Azure Speech, lo envia a un modelo
                  desplegado en Azure AI Foundry y responde en texto y voz.
                </p>
              </div>
            </div>

            <div className="status-pill">
              <span className={multimodalConfigured ? "status-dot ready" : "status-dot"} />
              <span>
                {multimodalConfigured
                  ? `Modelo listo${multimodalModel ? `: ${multimodalModel}` : ""}`
                  : "Configura FOUNDRY_ENDPOINT, FOUNDRY_API_KEY y FOUNDRY_MODEL"}
              </span>
            </div>

            <label className="drop-zone">
              <FileAudio size={24} />
              <span>{promptFile ? promptFile.name : "Seleccionar audio del prompt (WAV)"}</span>
              <input
                type="file"
                accept=".wav,audio/wav"
                onChange={(event) => setPromptFile(event.target.files?.[0] || null)}
              />
            </label>

            <label className="instructions-label">
              Instrucciones (opcional)
              <input
                type="text"
                placeholder="Ej: Responde en espanol y de forma concisa."
                value={instructions}
                onChange={(event) => setInstructions(event.target.value)}
              />
            </label>

            <button
              className="multimodal-action"
              type="button"
              onClick={respond}
              disabled={!promptFile || isResponding}
            >
              {isResponding ? <Loader2 className="spin" size={18} /> : <MessageSquare size={18} />}
              Responder al prompt
            </button>

            {recognizedPrompt && (
              <div className="transcript-box">
                <strong>Prompt reconocido</strong>
                <p>{recognizedPrompt}</p>
              </div>
            )}

            <div className="transcript-box">
              <strong>Respuesta del modelo</strong>
              <p>{answerText || "La respuesta del modelo aparecera aqui."}</p>
            </div>

            {answerAudioUrl && (
              <div className="audio-result">
                <Radio size={18} />
                <audio src={answerAudioUrl} controls />
              </div>
            )}
          </section>

          {error && <div className="error">{error}</div>}
        </section>
      </section>
    </main>
  );
}
