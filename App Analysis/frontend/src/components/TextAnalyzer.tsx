import { FormEvent, useMemo, useState } from "react";
import BarChart3 from "lucide-react/dist/esm/icons/bar-chart-3.js";
import FileText from "lucide-react/dist/esm/icons/file-text.js";
import Languages from "lucide-react/dist/esm/icons/languages.js";
import Loader2 from "lucide-react/dist/esm/icons/loader-2.js";
import ScanText from "lucide-react/dist/esm/icons/scan-text.js";
import Sparkles from "lucide-react/dist/esm/icons/sparkles.js";

type Sentiment = "positive" | "neutral" | "negative" | "mixed";

type AnalysisResult = {
  mode: "azure" | "local";
  language: {
    name: string;
    iso6391Name: string;
    confidenceScore: number;
  };
  sentiment: Sentiment;
  confidenceScores: {
    positive: number;
    neutral: number;
    negative: number;
  };
  keyPhrases: string[];
  entities: Array<{
    text: string;
    category: string;
    confidenceScore?: number;
  }>;
  stats: {
    characters: number;
    words: number;
    sentences: number;
    readingTimeMinutes: number;
  };
};

const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:3010";

const examples = [
  "Blockstellart está creando una experiencia excelente con Azure AI. El equipo avanzó rápido y el resultado fue muy útil para los usuarios.",
  "El servicio tardo demasiado y algunos clientes reportaron errores en la aplicacion durante la manana.",
  "Microsoft Azure AI Language permite detectar idioma, entidades, frases clave y sentimiento dentro de documentos de texto."
];

const sentimentLabels: Record<Sentiment, string> = {
  positive: "Positivo",
  neutral: "Neutral",
  negative: "Negativo",
  mixed: "Mixto"
};

export function TextAnalyzer() {
  const [text, setText] = useState(examples[0]);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState("");

  const canAnalyze = text.trim().length > 0 && !isAnalyzing;
  const dominantScore = useMemo(() => {
    if (!result) return 0;
    return Math.round(Math.max(...Object.values(result.confidenceScores)) * 100);
  }, [result]);

  async function handleAnalyze(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canAnalyze) return;

    setIsAnalyzing(true);
    setError("");

    try {
      const response = await fetch(`${apiUrl}/api/analyze`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ text })
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || data.error || "No se pudo analizar el texto.");
      }

      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error inesperado.");
    } finally {
      setIsAnalyzing(false);
    }
  }

  return (
    <main className="app-shell">
      <section className="workspace">
        <aside className="hero-panel">
          <div className="brand-mark" aria-hidden="true">
            <ScanText size={26} />
          </div>
          <div>
            <p className="eyebrow">Joan Amengual</p>
            <h1>Blockstellart - Analisis de texto</h1>
            <p className="hero-copy">
              Explora sentimiento, idioma, entidades y frases clave con una app ligera conectada a Azure AI Language.
            </p>
          </div>

          <div className="hero-stats">
            <div>
              <span>Fuente</span>
              <strong>{result?.mode === "azure" ? "Azure" : "Local"}</strong>
            </div>
            <div>
              <span>Endpoint</span>
              <strong>/api/analyze</strong>
            </div>
          </div>
        </aside>

        <section className="analysis-panel">
          <form className="input-card" onSubmit={handleAnalyze}>
            <div className="section-title">
              <FileText size={20} />
              <div>
                <h2>Texto de entrada</h2>
                <p>Pega una opinion, comentario o parrafo para analizarlo.</p>
              </div>
            </div>

            <textarea
              value={text}
              onChange={(event) => setText(event.target.value)}
              placeholder="Escribe aqui el texto..."
            />

            <div className="example-row">
              {examples.map((example, index) => (
                <button key={example} type="button" onClick={() => setText(example)}>
                  Ejemplo {index + 1}
                </button>
              ))}
            </div>

            <button className="primary-action" type="submit" disabled={!canAnalyze}>
              {isAnalyzing ? <Loader2 className="spin" size={18} /> : <Sparkles size={18} />}
              Analizar texto
            </button>
          </form>

          {error && <div className="error">{error}</div>}

          <div className="results-grid">
            <article className={`result-card sentiment ${result?.sentiment || "empty"}`}>
              <div className="section-title compact">
                <BarChart3 size={20} />
                <div>
                  <h2>Sentimiento</h2>
                  <p>{result ? `${dominantScore}% de confianza` : "Sin analisis todavia"}</p>
                </div>
              </div>
              <strong className="sentiment-value">
                {result ? sentimentLabels[result.sentiment] : "Pendiente"}
              </strong>
            </article>

            <article className="result-card">
              <div className="section-title compact">
                <Languages size={20} />
                <div>
                  <h2>Idioma</h2>
                  <p>{result ? `${Math.round(result.language.confidenceScore * 100)}% de confianza` : "Pendiente"}</p>
                </div>
              </div>
              <strong className="language-value">
                {result ? `${result.language.name} (${result.language.iso6391Name})` : "Sin detectar"}
              </strong>
            </article>

            <article className="result-card wide">
              <h2>Frases clave</h2>
              <div className="chips">
                {result?.keyPhrases.length ? (
                  result.keyPhrases.map((phrase) => <span key={phrase}>{phrase}</span>)
                ) : (
                  <p className="muted">Apareceran aqui despues del analisis.</p>
                )}
              </div>
            </article>

            <article className="result-card wide">
              <h2>Entidades</h2>
              <div className="entity-list">
                {result?.entities.length ? (
                  result.entities.map((entity) => (
                    <div key={`${entity.text}-${entity.category}`}>
                      <strong>{entity.text}</strong>
                      <span>{entity.category}</span>
                    </div>
                  ))
                ) : (
                  <p className="muted">No hay entidades detectadas todavia.</p>
                )}
              </div>
            </article>

            <article className="result-card wide stats">
              <h2>Metricas del texto</h2>
              <div>
                <span>{result?.stats.words || 0} palabras</span>
                <span>{result?.stats.characters || 0} caracteres</span>
                <span>{result?.stats.sentences || 0} oraciones</span>
                <span>{result?.stats.readingTimeMinutes || 0} min lectura</span>
              </div>
            </article>
          </div>
        </section>
      </section>
    </main>
  );
}
