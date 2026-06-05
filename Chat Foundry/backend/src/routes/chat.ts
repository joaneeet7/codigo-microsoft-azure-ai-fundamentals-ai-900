import { Router } from "express";
import { openAIClient, modelDeploymentName } from "../foundryClient.js";

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

type ChatRequest = {
  message?: string;
  history?: ChatMessage[];
};

const router = Router();

router.post("/", async (req, res) => {
  const { message, history = [] } = req.body as ChatRequest;

  if (!message || !message.trim()) {
    res.status(400).json({ error: "message is required" });
    return;
  }

  try {
    const transcript = history
      .map((item) => `${item.role === "user" ? "Usuario" : "Asistente"}: ${item.content}`)
      .join("\n");

    const input = [
      "Eres un asistente de demo para una app ligera de chat.",
      "Responde en espanol, con claridad y de forma concisa.",
      "",
      transcript ? `Historial:\n${transcript}\n` : "Historial: conversacion nueva.\n",
      `Usuario: ${message.trim()}`,
      "Asistente:"
    ].join("\n");

    const response = await openAIClient.responses.create({
      model: modelDeploymentName,
      input
    });

    res.json({
      answer: response.output_text || "No pude generar una respuesta.",
      model: modelDeploymentName
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Unexpected Foundry SDK error";

    res.status(500).json({
      error: "Foundry request failed",
      detail: message
    });
  }
});

export default router;
