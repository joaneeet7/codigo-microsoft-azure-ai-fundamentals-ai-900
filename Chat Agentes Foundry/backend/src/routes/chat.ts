import { Router } from "express";
import { openAIClient } from "../foundryClient.js";

type ChatRequest = {
  agentName?: string;
  message?: string;
  conversationId?: string;
};

const router = Router();

router.post("/", async (req, res) => {
  const { agentName, message, conversationId } = req.body as ChatRequest;

  if (!agentName || !agentName.trim()) {
    res.status(400).json({ error: "agentName is required" });
    return;
  }

  if (!message || !message.trim()) {
    res.status(400).json({ error: "message is required" });
    return;
  }

  try {
    let activeConversationId = conversationId;

    if (!activeConversationId) {
      const conversation = await openAIClient.conversations.create();
      activeConversationId = conversation.id;
    }

    const response = await openAIClient.responses.create(
      {
        conversation: activeConversationId,
        input: message.trim()
      },
      {
        body: { agent: { name: agentName.trim(), type: "agent_reference" } }
      }
    );

    res.json({
      answer: response.output_text || "No pude generar una respuesta.",
      conversationId: activeConversationId,
      agentName
    });
  } catch (error) {
    const detail =
      error instanceof Error ? error.message : "Unexpected Foundry SDK error";

    res.status(500).json({
      error: "Foundry request failed",
      detail
    });
  }
});

export default router;
