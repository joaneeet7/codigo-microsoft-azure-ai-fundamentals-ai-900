import { ChangeEvent, FormEvent, ReactNode, useEffect, useMemo, useState } from "react";
import AlertCircle from "lucide-react/dist/esm/icons/alert-circle.js";
import Boxes from "lucide-react/dist/esm/icons/boxes.js";
import FileImage from "lucide-react/dist/esm/icons/file-image.js";
import ImageUp from "lucide-react/dist/esm/icons/image-up.js";
import Loader2 from "lucide-react/dist/esm/icons/loader-2.js";
import ScanEye from "lucide-react/dist/esm/icons/scan-eye.js";
import Sparkles from "lucide-react/dist/esm/icons/sparkles.js";
import Tags from "lucide-react/dist/esm/icons/tags.js";
import Type from "lucide-react/dist/esm/icons/type.js";
import Users from "lucide-react/dist/esm/icons/users.js";

const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:3050";
const defaultSelectedFeatures = ["caption", "denseCaptions", "tags", "objects", "read", "people"];

const featureOptions = [
  { id: "caption", label: "Caption" },
  { id: "denseCaptions", label: "Dense" },
  { id: "tags", label: "Tags" },
  { id: "objects", label: "Objects" },
  { id: "read", label: "OCR" },
  { id: "people", label: "People" },
  { id: "smartCrops", label: "Crops" }
];

type VisionSummary = {
  caption?: string;
  tags: string[];
  objects: string[];
  people: number;
  denseCaptions: string[];
  readLines: string[];
};

type VisionResult = {
  mode: "azure" | "demo";
  fileName: string;
  contentType: string;
  bytes: number;
  features: string[];
  summary: VisionSummary;
  raw: unknown;
};

export function VisionLab() {
  const [configured, setConfigured] = useState(false);
  const [apiVersion, setApiVersion] = useState("2024-02-01");
  const [selectedFeatures, setSelectedFeatures] = useState(defaultSelectedFeatures);
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [result, setResult] = useState<VisionResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const fileSize = useMemo(() => {
    if (!file) return "Sin imagen";
    return `${Math.max(1, Math.round(file.size / 1024))} KB`;
  }, [file]);

  useEffect(() => {
    async function loadConfig() {
      try {
        const response = await fetch(`${apiUrl}/api/config`);
        const data = await response.json();
        setConfigured(Boolean(data.configured));
        setApiVersion(data.apiVersion || "2024-02-01");
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

  function toggleFeature(feature: string) {
    setSelectedFeatures((current) => {
      if (current.includes(feature)) {
        const next = current.filter((item) => item !== feature);
        return next.length ? next : current;
      }
      return [...current, feature];
    });
  }

  async function analyze(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file || isLoading) return;

    const body = new FormData();
    body.append("image", file);
    body.append("features", selectedFeatures.join(","));

    setIsLoading(true);
    setError("");

    try {
      const response = await fetch(`${apiUrl}/api/analyze`, {
        method: "POST",
        body
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "No se pudo analizar la imagen.");
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
            <p className="eyebrow">Azure AI Vision</p>
            <h1>App Vision</h1>
            <p className="intro">
              Analiza imagenes con caption, etiquetas, objetos, OCR, personas y recortes inteligentes.
            </p>
          </div>

          <div className="status-box">
            <span className={configured ? "status-dot ready" : "status-dot"} />
            <div>
              <strong>{configured ? "Vision conectado" : "Modo demo local"}</strong>
              <p>{configured ? `API ${apiVersion}` : "Configura VISION_ENDPOINT y VISION_KEY."}</p>
            </div>
          </div>
        </aside>

        <section className="workbench">
          <form className="input-panel" onSubmit={analyze}>
            <div className="section-title">
              <ImageUp size={20} />
              <div>
                <h2>Entrada visual</h2>
                <p>Sube una imagen y elige las capacidades de analisis.</p>
              </div>
            </div>

            <label className={previewUrl ? "drop-zone has-image" : "drop-zone"}>
              <input type="file" accept="image/png,image/jpeg,image/webp,image/bmp,image/gif" onChange={onFileChange} />
              {previewUrl ? (
                <img src={previewUrl} alt="Vista previa" />
              ) : (
                <span>
                  <FileImage size={34} />
                  Seleccionar imagen
                </span>
              )}
            </label>

            <div className="meta-row">
              <span><FileImage size={16} /> {file?.name || "PNG, JPG, WEBP, BMP o GIF"}</span>
              <span>{fileSize}</span>
            </div>

            <div className="feature-grid">
              {featureOptions.map((feature) => (
                <button
                  type="button"
                  key={feature.id}
                  className={selectedFeatures.includes(feature.id) ? "feature-chip active" : "feature-chip"}
                  onClick={() => toggleFeature(feature.id)}
                >
                  {feature.label}
                </button>
              ))}
            </div>

            <button className="primary-action" type="submit" disabled={!file || isLoading}>
              {isLoading ? <Loader2 className="spin" size={18} /> : <Sparkles size={18} />}
              Analizar imagen
            </button>
          </form>

          <section className="result-panel">
            <div className="section-title">
              <ScanEye size={20} />
              <div>
                <h2>Resultados de vision</h2>
                <p>{result ? `${result.mode} - ${result.features.join(", ")}` : "El analisis aparecera aqui."}</p>
              </div>
            </div>

            {error && (
              <div className="error-box">
                <AlertCircle size={18} />
                <p>{error}</p>
              </div>
            )}

            <div className="result-grid">
              <ResultCard icon={<Sparkles size={18} />} title="Caption" value={result?.summary.caption || "Sin caption todavia."} />
              <ResultCard icon={<Tags size={18} />} title="Tags" value={result?.summary.tags.join(", ") || "Sin etiquetas."} />
              <ResultCard icon={<Boxes size={18} />} title="Objetos" value={result?.summary.objects.join(", ") || "Sin objetos detectados."} />
              <ResultCard icon={<Users size={18} />} title="Personas" value={result ? String(result.summary.people) : "-"} />
            </div>

            <section className="detail-section">
              <h3>Dense captions</h3>
              {result?.summary.denseCaptions.length ? (
                result.summary.denseCaptions.map((item, index) => <p key={`${item}-${index}`}>{item}</p>)
              ) : (
                <p>Sin captions detallados.</p>
              )}
            </section>

            <section className="detail-section">
              <h3><Type size={16} /> OCR</h3>
              {result?.summary.readLines.length ? (
                result.summary.readLines.map((item, index) => <p key={`${item}-${index}`}>{item}</p>)
              ) : (
                <p>Sin texto detectado.</p>
              )}
            </section>

            {result && (
              <details className="raw-box">
                <summary>Ver respuesta JSON</summary>
                <pre>{JSON.stringify(result.raw, null, 2)}</pre>
              </details>
            )}
          </section>
        </section>
      </section>
    </main>
  );
}

function ResultCard({ icon, title, value }: { icon: ReactNode; title: string; value: string }) {
  return (
    <article className="result-card">
      <span>{icon}</span>
      <div>
        <strong>{title}</strong>
        <p>{value}</p>
      </div>
    </article>
  );
}