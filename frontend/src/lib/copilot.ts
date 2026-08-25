import { apiClient } from "./apiClient";

export type AttachmentPayload = {
  filename: string;
  file_type: string;
  extracted_text: string;
  file_data?: string | null;
  is_resume?: boolean;
};

export type AttachmentUploadOut = {
  filename: string;
  file_type: string;
  extracted_text: string;
  file_data?: string | null;
  char_count: number;
  is_resume: boolean;
  resume_hint?: string | null;
};

export type ChatMessage = {
  role: "user" | "assistant";
  text: string;
  grounded?: boolean;
  attachment?: AttachmentPayload | null;
  resume_suggestion?: string | null;
  created_at?: string;
};

export type ConversationSummary = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  last_preview: string;
};

export type ConversationDetail = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: ChatMessage[];
};

export async function uploadAttachment(file: File): Promise<AttachmentUploadOut> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await apiClient.post<AttachmentUploadOut>("/copilot/attachment", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
}

export async function listConversations(): Promise<ConversationSummary[]> {
  const res = await apiClient.get<ConversationSummary[]>("/copilot/conversations");
  return res.data;
}

export async function createConversation(title?: string): Promise<ConversationDetail> {
  const res = await apiClient.post<ConversationDetail>("/copilot/conversations", { title });
  return res.data;
}

export async function getConversation(convId: string): Promise<ConversationDetail> {
  const res = await apiClient.get<ConversationDetail>(`/copilot/conversations/${convId}`);
  return res.data;
}

export async function renameConversation(convId: string, title: string): Promise<{ success: boolean; title: string }> {
  const res = await apiClient.patch<{ success: boolean; title: string }>(`/copilot/conversations/${convId}`, { title });
  return res.data;
}

export async function deleteConversation(convId: string): Promise<void> {
  await apiClient.delete(`/copilot/conversations/${convId}`);
}

export async function sendChatMessage(
  message: string,
  conversationId?: string,
  attachment?: AttachmentPayload
): Promise<{ reply: string; grounded: boolean; conversation_id: string; resume_suggestion?: string | null }> {
  const res = await apiClient.post<{
    reply: string;
    grounded: boolean;
    conversation_id: string;
    resume_suggestion?: string | null;
  }>("/copilot/message", {
    message,
    conversation_id: conversationId,
    attachment,
  });
  return res.data;
}

export async function getChatHistory(): Promise<ChatMessage[]> {
  const res = await apiClient.get<{ messages: ChatMessage[] }>("/copilot/history");
  return res.data.messages;
}

export async function clearChatHistory(): Promise<void> {
  await apiClient.delete("/copilot/history");
}
