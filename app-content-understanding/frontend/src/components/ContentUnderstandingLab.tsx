import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from "react";
import AlertCircle from "lucide-react/dist/esm/icons/alert-circle.js";
import Database from "lucide-react/dist/esm/icons/database.js";
import FileSearch from "lucide-react/dist/esm/icons/file-search.js";
import FileText from "lucide-react/dist/esm/icons/file-text.js";
import Loader2 from "lucide-react/dist/esm/icons/loader-2.js";
import ScanLine from "lucide-react/dist/esm/icons/scan-line.js";
import TableProperties from "lucide-react/dist/esm/icons/table-properties.js";

const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:3060";

const analyzerLabels: Record<string, string> = {
  "prebuilt-invoice": "Factura",
  "prebuilt-documentSearch": "Documento",
  "prebuilt-imageSearch": "Imagen",
  "prebuilt-tax.us.w2": "Tax W-2",
  "prebuilt-tax.us.w4": "Tax W-4",
  "prebuilt-tax.us.1099NEC": "Tax 1099-NEC"
};

type FieldRow = {
  name: string;
  type?: string;
  value: unknown;
  confidence?: number;
};

type AnalyzeResult = {
  mode: "azure" | "demo";
  analyzerId: string;
  fileName: string;
  contentType: string;
  bytes: number;
  summary: {
    status: string;
    markdown: string;
    fields: FieldRow[];
    pageCount: number;
    tableCount: number;
    keyValueCount: number;
    usage: unknown;
  };
  raw: unknown;
};

export function ContentUnderstandingLab() {
  const [configured, setConfigured] = useState(false);
  const [apiVersion, setApiVersion] = useState("2025-11-01");
  const [analyzers, setAnalyzers] = useState(Object.keys(analyzerLabels));
  const [analyzerId, setAnalyzerId] = useState("prebuilt-invoice");
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<AnalyzeResult | null>(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const fileSize = useMemo(() => {
    if (!file) return "Sin archivo";
    return `${Math.max(1, Math.round(file.size / 1024))} KB`;
  }, [file]);

  useEffect(() => {
    async function loadConfig() {
      try {
        const response = await fetch(`${apiUrl}/api/config`);
        const data = await response.json();
        setConfigured(Boolean(data.configured));
        setApiVersion(data.apiVersion || "2025-11-01");
        setAnalyzers(data.analyzers || Object.keys(analyzerLabels));
      } catch {
        setConfigured(false);
      }
    }

    loadConfig();
  }, []);

  function onFileChange(event: ChangeEvent<HTMLInputElement>) {
    setFile(event.target.files?.[0] || null);
    setResult(null);
    setError("");
  }

  async function analyze(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file || isLoading) return;

    const body = new FormData();
    body.append("file", file);
    body.append("analyzer_id", analyzerId);

    setError("");
    setIsLoading(true);

    try {
      const response = await fetch(`${apiUrl}/api/analyze`, { method: "POST", body });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "No se pudo analizar el archivo.");
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
            <div className="brand-mark" aria-hidden="true"><FileSearch size={30} /></div>
            <p className="eyebrow">Foundry Tools</p>
            <h1>Content Understanding</h1>
            <p className="intro">Extrae campos, tablas, texto y estructura desde documentos y formularios.</p>
          </div>
          <div className="status-box">
            <span className={configured ? "status-dot ready" : "status-dot"} />
            <div>
              <strong>{configured ? "Azure conectado" : "Modo demo local"}</strong>
              <p>{configured ? `API ${apiVersion}` : "Configura endpoint y key en backend/.env."}</p>
            </div>
          </div>
        </aside>

        <section className="workbench">
          <form className="input-panel" onSubmit={analyze}>
            <div className="section-title">
              <ScanLine size={20} />
              <div>
                <h2>Documento o formulario</h2>
                <p>Selecciona un analyzer y sube PDF, imagen o texto.</p>
              </div>
            </div>

            <label className="drop-zone">
              <input type="file" accept="application/pdf,image/jpeg,image/png,image/webp,image/tiff,text/plain" onChange={onFileChange} />
              <span><FileText size={34} />{file?.name || "Seleccionar archivo"}</span>
            </label>

            <div className="meta-row"><span>{file?.type || "PDF, JPG, PNG, WEBP, TIFF o TXT"}</span><span>{fileSize}</span></div>

            <label className="select-label">
              Analyzer
              <select value={analyzerId} onChange={(event) => setAnalyzerId(event.target.value)}>
                {analyzers.map((item) => <option key={item} value={item}>{analyzerLabels[item] || item}</option>)}
              </select>
            </label>

            <button className="primary-action" type="submit" disabled={!file || isLoading}>
              {isLoading ? <Loader2 className="spin" size={18} /> : <Database size={18} />}
              Extraer informacion
            </button>
          </form>

          <section className="result-panel">
            <div className="section-title">
              <TableProperties size={20} />
              <div>
                <h2>Informacion extraida</h2>
                <p>{result ? `${result.mode} - ${result.analyzerId}` : "Los campos apareceran aqui."}</p>
              </div>
            </div>

            {error && <div className="error-box"><AlertCircle size={18} /><p>{error}</p></div>}

            <div className="stats-grid">
              <Stat label="Paginas" value={result ? String(result.summary.pageCount) : "-"} />
              <Stat label="Tablas" value={result ? String(result.summary.tableCount) : "-"} />
              <Stat label="Key-values" value={result ? String(result.summary.keyValueCount) : "-"} />
            </div>

            <section className="fields-table">
              <h3>Campos</h3>
              {result?.summary.fields.length ? (
                result.summary.fields.map((field) => (
                  <article key={field.name}>
                    <strong>{field.name}</strong>
                    <span>{formatValue(field.value)}</span>
                    <em>{field.confidence == null ? "" : `${Math.round(field.confidence * 100)}%`}</em>
                  </article>
                ))
              ) : <p>Sin campos extraidos todavia.</p>}
            </section>

            <section className="markdown-box">
              <h3>Markdown</h3>
              <pre>{result?.summary.markdown || "Sin contenido todavia."}</pre>
            </section>

            {result && <details className="raw-box"><summary>Ver JSON</summary><pre>{JSON.stringify(result.raw, null, 2)}</pre></details>}
          </section>
        </section>
      </section>
    </main>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return <article className="stat-card"><strong>{value}</strong><span>{label}</span></article>;
}

function formatValue(value: unknown): string {
  if (value == null) return "-";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value);
}