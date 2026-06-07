import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import Bot from "lucide-react/dist/esm/icons/bot.js";
import Loader2 from "lucide-react/dist/esm/icons/loader-2.js";
import RefreshCw from "lucide-react/dist/esm/icons/refresh-cw.js";
import Send from "lucide-react/dist/esm/icons/send.js";
import Sparkles from "lucide-react/dist/esm/icons/sparkles.js";
import Trash2 from "lucide-react/dist/esm/icons/trash-2.js";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

type Agent = {
  id: string;
  name: string;
  description: string;
  version: string;
  model: string;
};

const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:3001";

function createId() {
  return crypto.randomUUID();
}

export function Chat() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState("");
  const [agentsLoading, setAgentsLoading] = useState(true);
  const [agentsError, setAgentsError] = useState("");

  const [messages, setMessages] = useState<Message[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const activeAgent = useMemo(
    () => agents.find((agent) => agent.name === selectedAgent),
    [agents, selectedAgent]
  );

  async function loadAgents() {
    setAgentsLoading(true);
    setAgentsError("");

    try {
      const response = await fetch(`${apiUrl}/api/agents`);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || data.error || "No se pudieron cargar los agentes.");
      }

      const list: Agent[] = data.agents ?? [];
      setAgents(list);

      if (list.length > 0) {
        setSelectedAgent((current) =>
          current && list.some((agent) => agent.name === current)
            ? current
            : list[0].name
        );
      }
    } catch (err) {
      setAgentsError(err instanceof Error ? err.message : "Error inesperado.");
    } finally {
      setAgentsLoading(false);
    }
  }

  useEffect(() => {
    loadAgents();
  }, []);

  function resetConversation() {
    setMessages([]);
    setConversationId(null);
    setError("");
    inputRef.current?.focus();
  }

  function handleAgentChange(name: string) {
    setSelectedAgent(name);
    setMessages([]);
    setConversationId(null);
    setError("");
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const trimmed = input.trim();
    if (!trimmed || isSending || !selectedAgent) return;

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
          agentName: selectedAgent,
          message: trimmed,
          conversationId
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || data.error || "No se pudo enviar el mensaje.");
      }

      setConversationId(data.conversationId ?? null);
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

  return (
    <main className="shell">
      <section className="chat-panel" aria-label="Chat con agentes de Foundry">
        <header className="chat-header">
          <div className="brand-mark" aria-hidden="true">
            <Bot size={20} />
          </div>
          <div>
            <h1>Blockstellart agentes</h1>
            <p>Joan Amengual</p>
          </div>
          <button className="icon-button" type="button" onClick={resetConversation} title="Limpiar conversacion">
            <Trash2 size={18} />
          </button>
        </header>

        <div className="agent-bar">
          <label className="agent-field">
            <span>Agente</span>
            <select
              value={selectedAgent}
              onChange={(event) => handleAgentChange(event.target.value)}
              disabled={agentsLoading || agents.length === 0}
            >
              {agents.length === 0 ? (
                <option value="">{agentsLoading ? "Cargando agentes..." : "Sin agentes"}</option>
              ) : (
                agents.map((agent) => (
                  <option key={agent.id || agent.name} value={agent.name}>
                    {agent.name}
                    {agent.model ? ` (${agent.model})` : ""}
                  </option>
                ))
              )}
            </select>
          </label>
          <button
            className="icon-button"
            type="button"
            onClick={loadAgents}
            disabled={agentsLoading}
            title="Recargar agentes"
          >
            <RefreshCw className={agentsLoading ? "spin" : ""} size={18} />
          </button>
        </div>

        {activeAgent?.description && (
          <p className="agent-description">{activeAgent.description}</p>
        )}

        {agentsError && <div className="error">{agentsError}</div>}

        <div className="messages" aria-live="polite">
          {messages.length === 0 ? (
            <div className="empty-state">
              <Sparkles size={28} />
              <p>
                {selectedAgent
                  ? `Escribe tu primer mensaje para hablar con ${selectedAgent}.`
                  : "Selecciona un agente para comenzar."}
              </p>
            </div>
          ) : (
            messages.map((message) => (
              <article className={`message ${message.role}`} key={message.id}>
                <span>{message.role === "user" ? "Tu" : selectedAgent || "Agente"}</span>
                <p>{message.content}</p>
              </article>
            ))
          )}

          {isSending && (
            <article className="message assistant pending">
              <span>{selectedAgent || "Agente"}</span>
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
            placeholder={selectedAgent ? "Escribe un mensaje..." : "Selecciona un agente primero..."}
            rows={1}
            disabled={!selectedAgent}
          />
          <button
            type="submit"
            disabled={!input.trim() || isSending || !selectedAgent}
            title="Enviar mensaje"
          >
            {isSending ? <Loader2 className="spin" size={18} /> : <Send size={18} />}
          </button>
        </form>
      </section>
    </main>
  );
}
