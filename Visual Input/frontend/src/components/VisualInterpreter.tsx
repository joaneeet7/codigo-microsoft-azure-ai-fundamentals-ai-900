import { ChangeEvent, FormEvent, ReactNode, useEffect, useMemo, useState } from "react";
import AlertCircle from "lucide-react/dist/esm/icons/alert-circle.js";
import BrainCircuit from "lucide-react/dist/esm/icons/brain-circuit.js";
import FileImage from "lucide-react/dist/esm/icons/file-image.js";
import ImageUp from "lucide-react/dist/esm/icons/image-up.js";
import Loader2 from "lucide-react/dist/esm/icons/loader-2.js";
import ScanEye from "lucide-react/dist/esm/icons/scan-eye.js";
import Sparkles from "lucide-react/dist/esm/icons/sparkles.js";

const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:3040";

const starterPrompt =
  "Interpreta la imagen para construir un prompt visual: describe objetos principales, contexto, estilo, colores, iluminacion, composicion y posibles mejoras.";

function renderInlineMarkdown(text: string): ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={`${part}-${index}`}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}

function renderMarkdown(text: string): ReactNode[] {
  return text.split(/\r?\n/).map((line, index) => {
    const trimmed = line.trim();

    if (!trimmed) {
      return <div key={index} className="md-spacer" />;
    }

    if (trimmed.startsWith("### ")) {
      return <h3 key={index}>{renderInlineMarkdown(trimmed.slice(4))}</h3>;
    }

    if (trimmed.startsWith("## ")) {
      return <h3 key={index}>{renderInlineMarkdown(trimmed.slice(3))}</h3>;
    }

    if (trimmed.startsWith("# ")) {
      return <h3 key={index}>{renderInlineMarkdown(trimmed.slice(2))}</h3>;
    }

    const bullet = trimmed.match(/^[-*]\s+(.*)$/);
    if (bullet) {
      return (
        <p key={index} className="md-list-item">
          <span aria-hidden="true">-</span>
          <span>{renderInlineMarkdown(bullet[1])}</span>
        </p>
      );
    }

    return <p key={index}>{renderInlineMarkdown(trimmed)}</p>;
  });
}
type AnalysisResult = {
  mode: "azure" | "demo";
  analysis: string;
  fileName: string;
  contentType: string;
  bytes: number;
  deployment: string;
};

export function VisualInterpreter() {
  const [configured, setConfigured] = useState(false);
  const [deployment, setDeployment] = useState("gpt-4o-mini");
  const [prompt, setPrompt] = useState(starterPrompt);
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const fileSize = useMemo(() => {
    if (!file) return "Sin imagen";
    const kb = Math.max(1, Math.round(file.size / 1024));
    return `${kb} KB`;
  }, [file]);

  useEffect(() => {
    async function loadConfig() {
      try {
        const response = await fetch(`${apiUrl}/api/config`);
        const data = await response.json();
        setConfigured(Boolean(data.configured));
        setDeployment(data.deployment || "gpt-4o-mini");
      } catch {
        setConfigured(false);
      }
    }

    loadConfig();
  }, []);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  function onFileChange(event: ChangeEvent<HTMLInputElement>) {
    const nextFile = event.target.files?.[0] || null;
    setFile(nextFile);
    setResult(null);
    setError("");

    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(nextFile ? URL.createObjectURL(nextFile) : "");
  }

  async function analyze(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file || !prompt.trim() || isLoading) return;

    const body = new FormData();
    body.append("prompt", prompt.trim());
    body.append("image", file);

    setError("");
    setIsLoading(true);

    try {
      const response = await fetch(`${apiUrl}/api/analyze-visual`, {
        method: "POST",
        body
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "No se pudo interpretar la imagen.");
      }

      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error inesperado.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="app-shell">
      <section className="layout">
        <aside className="side-panel">
          <div>
            <div className="brand-mark" aria-hidden="true">
              <ScanEye size={30} />
            </div>
            <p className="eyebrow">Entrada visual multimodal</p>
            <h1>Visual Input</h1>
            <p className="intro">
              Interpreta imagenes dentro de prompts usando un modelo multimodal desplegado.
            </p>
          </div>

          <div className="status-box">
            <span className={configured ? "status-dot ready" : "status-dot"} />
            <div>
              <strong>{configured ? "Azure conectado" : "Modo demo local"}</strong>
              <p>{configured ? `Deployment: ${deployment}` : "Backend activo sin credenciales Azure."}</p>
            </div>
          </div>
        </aside>

        <section className="workbench">
          <form className="input-panel" onSubmit={analyze}>
            <div className="section-title">
              <Sparkles size={20} />
              <div>
                <h2>Prompt multimodal</h2>
                <p>Combina instruccion textual con una entrada visual.</p>
              </div>
            </div>

            <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} />

            <label className={previewUrl ? "drop-zone has-image" : "drop-zone"}>
              <input type="file" accept="image/png,image/jpeg,image/webp" onChange={onFileChange} />
              {previewUrl ? (
                <img src={previewUrl} alt="Vista previa" />
              ) : (
                <span>
                  <ImageUp size={34} />
                  Seleccionar imagen
                </span>
              )}
            </label>

            <div className="meta-row">
              <span><FileImage size={16} /> {file?.name || "PNG, JPG o WEBP"}</span>
              <span>{fileSize}</span>
            </div>

            <button className="primary-action" type="submit" disabled={!file || !prompt.trim() || isLoading}>
              {isLoading ? <Loader2 className="spin" size={18} /> : <BrainCircuit size={18} />}
              Interpretar entrada visual
            </button>
          </form>

          <section className="result-panel">
            <div className="section-title">
              <BrainCircuit size={20} />
              <div>
                <h2>Interpretacion</h2>
                <p>{result ? `${result.mode} - ${result.deployment}` : "El resultado aparecera aqui."}</p>
              </div>
            </div>

            {error && (
              <div className="error-box">
                <AlertCircle size={18} />
                <p>{error}</p>
              </div>
            )}

            <article className="analysis-box">
              {result ? <div className="markdown-body">{renderMarkdown(result.analysis)}</div> : "Sin analisis todavia."}
            </article>
          </section>
        </section>
      </section>
    </main>
  );
}