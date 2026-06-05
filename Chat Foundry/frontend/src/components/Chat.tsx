import { FormEvent, useMemo, useRef, useState } from "react";
import Loader2 from "lucide-react/dist/esm/icons/loader-2.js";
import Send from "lucide-react/dist/esm/icons/send.js";
import Sparkles from "lucide-react/dist/esm/icons/sparkles.js";
import Trash2 from "lucide-react/dist/esm/icons/trash-2.js";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:3001";

function createId() {
  return crypto.randomUUID();
}

export function Chat() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: createId(),
      role: "assistant",
      content:
        "Hola. Soy tu demo de chat con Foundry SDK. Preguntame algo para probar la conexion."
    }
  ]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const history = useMemo(
    () =>
      messages
        .filter((message) => message.role === "user" || message.role === "assistant")
        .map(({ role, content }) => ({ role, content })),
    [messages]
  );

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const trimmed = input.trim();
    if (!trimmed || isSending) return;

    const userMessage: Message = {
      id: createId(),
      role: "user",
      content: trimmed
    };

    setMessages((current) => [...current, userMessage]);
    setInput("");
    setError("");
    setIsSending(true);

    try {
      const response = await fetch(`${apiUrl}/api/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          message: trimmed,
          history
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || data.error || "No se pudo enviar el mensaje.");
      }

      setMessages((current) => [
        ...current,
        {
          id: createId(),
          role: "assistant",
          content: data.answer
        }
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error inesperado.");
    } finally {
      setIsSending(false);
      inputRef.current?.focus();
    }
  }

  function clearChat() {
    setMessages([]);
    setError("");
    inputRef.current?.focus();
  }

  return (
    <main className="shell">
      <section className="chat-panel" aria-label="Chat con Foundry SDK">
        <header className="chat-header">
          <div className="brand-mark" aria-hidden="true">
            <Sparkles size={20} />
          </div>
          <div>
            <h1>Blockstellart chat</h1>
            <p>Joan Amengual</p>
          </div>
          <button className="icon-button" type="button" onClick={clearChat} title="Limpiar chat">
            <Trash2 size={18} />
          </button>
        </header>

        <div className="messages" aria-live="polite">
          {messages.length === 0 ? (
            <div className="empty-state">
              <Sparkles size={28} />
              <p>Escribe tu primer mensaje para iniciar una conversacion.</p>
            </div>
          ) : (
            messages.map((message) => (
              <article className={`message ${message.role}`} key={message.id}>
                <span>{message.role === "user" ? "Tu" : "Foundry"}</span>
                <p>{message.content}</p>
              </article>
            ))
          )}

          {isSending && (
            <article className="message assistant pending">
              <span>Foundry</span>
              <p>
                <Loader2 className="spin" size={16} />
                Pensando...
              </p>
            </article>
          )}
        </div>

        {error && <div className="error">{error}</div>}

        <form className="composer" onSubmit={handleSubmit}>
          <textarea
            ref={inputRef}
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Escribe un mensaje..."
            rows={1}
          />
          <button type="submit" disabled={!input.trim() || isSending} title="Enviar mensaje">
            {isSending ? <Loader2 className="spin" size={18} /> : <Send size={18} />}
          </button>
        </form>
      </section>
    </main>
  );
}
