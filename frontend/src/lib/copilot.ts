import { apiClient } from "./apiClient";

export type ChatMessage = { role: "user" | "assistant"; text: string; grounded?: boolean };

export async function getChatHistory(): Promise<ChatMessage[]> {
  const res = await apiClient.get<{ messages: ChatMessage[] }>("/copilot/history");
  return res.data.messages;
}

export async function clearChatHistory(): Promise<void> {
  await apiClient.delete("/copilot/history");
}

export async function sendChatMessage(message: string): Promise<{ reply: string; grounded: boolean }> {
  const res = await apiClient.post<{ reply: string; grounded: boolean }>("/copilot/message", { message });
  return res.data;
}
