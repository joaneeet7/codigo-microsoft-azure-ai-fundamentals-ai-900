import { FormEvent, useEffect, useMemo, useState } from "react";
import Download from "lucide-react/dist/esm/icons/download.js";
import ImageIcon from "lucide-react/dist/esm/icons/image.js";
import Loader2 from "lucide-react/dist/esm/icons/loader-2.js";
import Palette from "lucide-react/dist/esm/icons/palette.js";
import Sparkles from "lucide-react/dist/esm/icons/sparkles.js";
import Wand2 from "lucide-react/dist/esm/icons/wand-2.js";

const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:3030";

const examples = [
  "Una ciudad futurista al amanecer, con arquitectura sustentable, jardines verticales y transporte autonomo, estilo editorial premium.",
  "Producto tecnologico flotando sobre una superficie de vidrio negro, iluminacion cinematografica, fondo minimalista azul y turquesa.",
  "Ilustracion conceptual de inteligencia artificial creando nuevas ideas visuales, composicion sofisticada, alto detalle."
];

type ImageResult = {
  mode: "azure" | "demo";
  image: string;
  prompt: string;
  size: string;
  quality: string;
  deployment: string;
};

export function ImageStudio() {
  const [prompt, setPrompt] = useState(examples[0]);
  const [size, setSize] = useState("1024x1024");
  const [quality, setQuality] = useState("medium");
  const [configured, setConfigured] = useState(false);
  const [deployment, setDeployment] = useState("gpt-image-1");
  const [result, setResult] = useState<ImageResult | null>(null);
  const [history, setHistory] = useState<ImageResult[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState("");

  const promptLength = useMemo(() => prompt.trim().length, [prompt]);

  useEffect(() => {
    async function loadConfig() {
      try {
        const response = await fetch(`${apiUrl}/api/config`);
        const data = await response.json();
        setConfigured(Boolean(data.configured));
        setDeployment(data.deployment || "gpt-image-1");
      } catch {
        setConfigured(false);
      }
    }

    loadConfig();
  }, []);

  async function generate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!prompt.trim() || isGenerating) return;

    setError("");
    setIsGenerating(true);

    try {
      const response = await fetch(`${apiUrl}/api/generate-image`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, size, quality })
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "No se pudo generar la imagen.");
      }

      setResult(data);
      setHistory((current) => [data, ...current].slice(0, 6));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error inesperado.");
    } finally {
      setIsGenerating(false);
    }
  }

  return (
    <main className="app-shell">
      <section className="workspace">
        <aside className="hero-panel">
          <div>
            <div className="brand-mark" aria-hidden="true">
              <Sparkles size={28} />
            </div>
            <p className="eyebrow">Modelos generativos</p>
            <h1>Visual Output Studio</h1>
            <p className="hero-copy">
              Crea salidas visuales a partir de instrucciones en lenguaje natural usando modelos generativos.
            </p>
          </div>

          <div className="status-card">
            <span className={configured ? "status-dot ready" : "status-dot"} />
            <div>
              <strong>{configured ? "Azure configurado" : "Modo demo local"}</strong>
              <p>{configured ? `Deployment: ${deployment}` : "Configura Azure OpenAI para imagen real."}</p>
            </div>
          </div>
        </aside>

        <section className="main-panel">
          <form className="prompt-card" onSubmit={generate}>
            <div className="card-title">
              <Wand2 size={20} />
              <div>
                <h2>Prompt visual</h2>
                <p>Describe la escena, estilo, iluminacion, composicion y proposito de la imagen.</p>
              </div>
            </div>

            <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} />

            <div className="example-row">
              {examples.map((example, index) => (
                <button type="button" key={example} onClick={() => setPrompt(example)}>
                  Prompt {index + 1}
                </button>
              ))}
            </div>

            <div className="controls">
              <label>
                Tamano
                <select value={size} onChange={(event) => setSize(event.target.value)}>
                  <option value="1024x1024">Cuadrado 1024</option>
                  <option value="1536x1024">Horizontal</option>
                  <option value="1024x1536">Vertical</option>
                </select>
              </label>
              <label>
                Calidad
                <select value={quality} onChange={(event) => setQuality(event.target.value)}>
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
              </label>
              <span>{promptLength} caracteres</span>
            </div>

            <button className="primary-action" type="submit" disabled={!prompt.trim() || isGenerating}>
              {isGenerating ? <Loader2 className="spin" size={18} /> : <Palette size={18} />}
              Generar salida visual
            </button>
          </form>

          {error && <div className="error">{error}</div>}

          <section className="preview-card">
            <div className="card-title compact">
              <ImageIcon size={20} />
              <div>
                <h2>Resultado</h2>
                <p>{result ? `${result.mode} · ${result.size} · ${result.quality}` : "La imagen generada aparecera aqui."}</p>
              </div>
            </div>

            <div className="preview-frame">
              {result ? <img src={result.image} alt="Salida visual generada" /> : <span>Sin imagen aun</span>}
            </div>

            {result && (
              <a className="download-action" href={result.image} download="salida-visual.png">
                <Download size={18} />
                Descargar imagen
              </a>
            )}
          </section>

          <section className="gallery-card">
            <h2>Historial visual</h2>
            <div className="gallery-grid">
              {history.length ? (
                history.map((item, index) => (
                  <button key={`${item.prompt}-${index}`} type="button" onClick={() => setResult(item)}>
                    <img src={item.image} alt={`Resultado ${index + 1}`} />
                    <span>{item.mode}</span>
                  </button>
                ))
              ) : (
                <p>Genera tu primera imagen para llenar la galeria.</p>
              )}
            </div>
          </section>
        </section>
      </section>
    </main>
  );
}
