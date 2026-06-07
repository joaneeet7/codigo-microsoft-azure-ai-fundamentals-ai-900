import { Router } from "express";
import { projectClient } from "../foundryClient.js";

const router = Router();

router.get("/", async (_req, res) => {
  try {
    const agents = [];

    for await (const agent of projectClient.agents.list()) {
      const latest = agent.versions?.latest;
      const definition = latest?.definition as { model?: string } | undefined;

      agents.push({
        id: agent.id,
        name: agent.name,
        description: latest?.description ?? "",
        version: latest?.version ?? "",
        model: definition?.model ?? ""
      });
    }

    res.json({ agents });
  } catch (error) {
    const detail =
      error instanceof Error ? error.message : "Unexpected Foundry SDK error";

    res.status(500).json({
      error: "No se pudieron listar los agentes",
      detail
    });
  }
});

export default router;
