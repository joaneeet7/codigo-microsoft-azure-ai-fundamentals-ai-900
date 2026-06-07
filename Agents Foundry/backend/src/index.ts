import "dotenv/config";
import cors from "cors";
import express from "express";
import agentsRouter from "./routes/agents.js";
import chatRouter from "./routes/chat.js";

const app = express();
const port = Number(process.env.PORT || 3001);
const allowedOrigin = process.env.ALLOWED_ORIGIN || "http://localhost:5173";

app.use(
  cors({
    origin: allowedOrigin
  })
);
app.use(express.json({ limit: "1mb" }));

app.get("/health", (_req, res) => {
  res.json({ ok: true });
});

app.use("/api/agents", agentsRouter);
app.use("/api/chat", chatRouter);

app.listen(port, () => {
  console.log(`Foundry agents backend running on http://localhost:${port}`);
});
