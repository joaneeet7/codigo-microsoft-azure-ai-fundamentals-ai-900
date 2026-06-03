import { AIProjectClient } from "@azure/ai-projects";
import { DefaultAzureCredential } from "@azure/identity";

const endpoint = process.env.PROJECT_ENDPOINT;

if (!endpoint) {
  throw new Error("PROJECT_ENDPOINT is required. Add it to backend/.env.");
}

export const modelDeploymentName =
  process.env.MODEL_DEPLOYMENT_NAME || "gpt-5-mini";

export const projectClient = new AIProjectClient(
  endpoint,
  new DefaultAzureCredential()
);

export const openAIClient = projectClient.getOpenAIClient();
