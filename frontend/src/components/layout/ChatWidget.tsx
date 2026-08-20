import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { MessageCircle, X, Send } from "lucide-react";
import { getChatHistory, sendChatMessage, type ChatMessage } from "../../lib/copilot";

const WELCOME: ChatMessage = {
  role: "assistant",
  text: "I'm your Career Copilot. I only answer from your real RoleRadar data — resume, matches, applications, skill gaps — so I'll tell you honestly when a feature isn't set up yet rather than guessing.",
};

export function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME]);

  const { data: history } = useQuery({
    queryKey: ["copilot-history"],
    queryFn: getChatHistory,
    enabled: open, // only fetch once the user actually opens the widget
  });

  useEffect(() => {
    if (history) setMessages(history.length > 0 ? history : [WELCOME]);
  }, [history]);

  const sendMessage = useMutation({
    mutationFn: sendChatMessage,
    onSuccess: (data) => {
      setMessages((prev) => [...prev, { role: "assistant", text: data.reply, grounded: data.grounded }]);
    },
    onError: () => {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: "Couldn't reach the Copilot. Make sure your local AI provider is running." },
      ]);
    },
  });

  function handleSend() {
    const trimmed = input.trim();
    if (!trimmed) return;
    setMessages((prev) => [...prev, { role: "user", text: trimmed }]);
    setInput("");
    sendMessage.mutate(trimmed);
  }

  return (
    <div className="fixed bottom-4 right-4 sm:bottom-6 sm:right-6 z-50">
      {open && (
        <div className="mb-3 w-[calc(100vw-2rem)] sm:w-80 max-w-sm rounded-xl border border-ink-100 bg-white shadow-2xl flex flex-col overflow-hidden animate-fade-in-up">
          <div className="bg-gradient-to-r from-ink-950 to-ink-900 px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <MessageCircle size={16} className="text-signal-400" />
              <p className="text-sm font-medium text-white">Career Copilot</p>
            </div>
            <button
              onClick={() => setOpen(false)}
              className="text-ink-400 hover:text-white sm:hidden p-1"
              aria-label="Close copilot"
            >
              <X size={16} />
            </button>
          </div>

          <div className="flex-1 max-h-80 overflow-y-auto px-4 py-3 space-y-3">
            {messages.map((m, i) => (
              <div key={i} className={m.role === "user" ? "text-right" : ""}>
                <p
                  className={`inline-block rounded-md px-3 py-2 text-sm leading-snug ${
                    m.role === "user" ? "bg-signal-500 text-white" : "bg-ink-50 text-ink-800"
                  }`}
                >
                  {m.text}
                </p>
                {m.grounded === false && (
                  <p className="mt-1 text-xs text-amber-600">Limited answer — some of your data isn't set up yet.</p>
                )}
              </div>
            ))}
            {sendMessage.isPending && <p className="text-xs text-ink-500">Thinking…</p>}
          </div>

          <div className="border-t border-ink-100 p-2 flex gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              placeholder="Ask about your jobs, gaps, applications…"
              className="flex-1 rounded-md border border-ink-100 px-2 py-1.5 text-sm outline-none focus:border-signal-500"
            />
            <button
              onClick={handleSend}
              className="rounded-md bg-ink-950 px-3 py-1.5 text-sm text-white hover:bg-ink-900 transition-transform active:scale-95"
              aria-label="Send"
            >
              <Send size={14} />
            </button>
          </div>
        </div>
      )}

      <button
        onClick={() => setOpen((v) => !v)}
        className="rounded-full bg-gradient-to-br from-signal-400 to-signal-600 hover:shadow-lg text-white w-14 h-14 shadow-md flex items-center justify-center transition-all duration-200 hover:scale-105 active:scale-95"
        aria-label="Open Career Copilot"
      >
        {open ? <X size={22} /> : <MessageCircle size={22} />}
      </button>
    </div>
  );
}
