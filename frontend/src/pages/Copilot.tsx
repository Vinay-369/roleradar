import { useEffect, useState, useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bot, Trash2, Send, Sparkles, Copy, Check, Download,
} from "lucide-react";
import { getChatHistory, clearChatHistory, sendChatMessage, type ChatMessage } from "../lib/copilot";

const WELCOME: ChatMessage = {
  role: "assistant",
  text: "### Welcome to Career Copilot! 👋\n\nI am your personalized AI career strategist. Ask me anything about:\n- **Your Resume ATS Compatibility & Bullet Metrics**\n- **Target Roles & Recommended Job Matches**\n- **Missing Skill Gaps & 4-Sprint Learning Roadmap**\n- **Interview Strategies, Frameworks & Salary Insights**\n\nType your question below to begin.",
};

function FormattedMarkdown({ content }: { content: string }) {
  const lines = content.split("\n");
  const elements: React.ReactNode[] = [];
  let listItems: string[] = [];

  function flushList() {
    if (listItems.length > 0) {
      elements.push(
        <ul key={`ul-${elements.length}`} className="my-2 space-y-1 pl-4 list-disc text-ink-800 marker:text-signal-600">
          {listItems.map((item, idx) => (
            <li key={idx} className="text-xs leading-relaxed pl-0.5">
              {formatInline(item)}
            </li>
          ))}
        </ul>
      );
      listItems = [];
    }
  }

  function formatInline(text: string): React.ReactNode[] {
    const parts: React.ReactNode[] = [];
    const regex = /(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)/g;
    let lastIndex = 0;
    let match: RegExpExecArray | null;

    while ((match = regex.exec(text)) !== null) {
      if (match.index > lastIndex) {
        parts.push(text.substring(lastIndex, match.index));
      }
      const token = match[0];
      if (token.startsWith("**") && token.endsWith("**")) {
        parts.push(
          <strong key={`b-${match.index}`} className="font-bold text-ink-950">
            {token.slice(2, -2)}
          </strong>
        );
      } else if (token.startsWith("`") && token.endsWith("`")) {
        parts.push(
          <code key={`c-${match.index}`} className="bg-ink-100 text-signal-800 px-1.5 py-0.5 rounded text-[11px] font-mono border border-ink-200/60 font-semibold">
            {token.slice(1, -1)}
          </code>
        );
      } else if (token.startsWith("*") && token.endsWith("*")) {
        parts.push(
          <em key={`i-${match.index}`} className="italic text-ink-700">
            {token.slice(1, -1)}
          </em>
        );
      }
      lastIndex = match.index + token.length;
    }

    if (lastIndex < text.length) {
      parts.push(text.substring(lastIndex));
    }

    return parts.length > 0 ? parts : [text];
  }

  lines.forEach((line, lineIdx) => {
    const trimmed = line.trim();

    if (trimmed.startsWith("### ")) {
      flushList();
      elements.push(
        <h3 key={`h3-${lineIdx}`} className="font-bold text-xs uppercase tracking-wider text-signal-700 mt-3 mb-1.5 flex items-center gap-1.5">
          <Sparkles size={13} className="text-signal-600 shrink-0" />
          {formatInline(trimmed.replace(/^###\s+/, ""))}
        </h3>
      );
    } else if (trimmed.startsWith("## ")) {
      flushList();
      elements.push(
        <h2 key={`h2-${lineIdx}`} className="font-bold text-sm text-ink-950 mt-3.5 mb-1.5">
          {formatInline(trimmed.replace(/^##\s+/, ""))}
        </h2>
      );
    } else if (trimmed.startsWith("# ")) {
      flushList();
      elements.push(
        <h1 key={`h1-${lineIdx}`} className="font-bold text-base text-ink-950 mt-4 mb-2">
          {formatInline(trimmed.replace(/^#\s+/, ""))}
        </h1>
      );
    } else if (trimmed.startsWith("- ") || trimmed.startsWith("* ") || trimmed.startsWith("• ")) {
      listItems.push(trimmed.replace(/^[-*•]\s+/, ""));
    } else if (/^\d+\.\s+/.test(trimmed)) {
      flushList();
      elements.push(
        <div key={`num-${lineIdx}`} className="flex gap-2 my-1 text-xs text-ink-800 leading-relaxed">
          <span className="font-bold text-signal-600 shrink-0">{trimmed.match(/^\d+\./)?.[0]}</span>
          <div>{formatInline(trimmed.replace(/^\d+\.\s+/, ""))}</div>
        </div>
      );
    } else if (trimmed === "") {
      flushList();
    } else {
      flushList();
      elements.push(
        <p key={`p-${lineIdx}`} className="my-1.5 text-xs text-ink-800 leading-relaxed">
          {formatInline(trimmed)}
        </p>
      );
    }
  });

  flushList();

  return <div className="space-y-0.5">{elements}</div>;
}

export function Copilot() {
  const queryClient = useQueryClient();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { data: history, isLoading } = useQuery({ queryKey: ["copilot-history"], queryFn: getChatHistory });
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME]);
  const [input, setInput] = useState("");
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  useEffect(() => {
    if (history) setMessages(history.length > 0 ? history : [WELCOME]);
  }, [history]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = useMutation({
    mutationFn: sendChatMessage,
    onSuccess: (data) => setMessages((prev) => [...prev, { role: "assistant", text: data.reply, grounded: data.grounded }]),
    onError: () =>
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: "### Connection Notice\n\nI couldn't process your question right now. Please verify your connection and try again.",
        },
      ]),
  });

  const clear = useMutation({
    mutationFn: clearChatHistory,
    onSuccess: () => {
      setMessages([WELCOME]);
      queryClient.invalidateQueries({ queryKey: ["copilot-history"] });
    },
  });

  function handleSend(textToSend?: string) {
    const query = (textToSend || input).trim();
    if (!query || send.isPending) return;
    setMessages((prev) => [...prev, { role: "user", text: query }]);
    if (!textToSend) setInput("");
    send.mutate(query);
  }

  function handleCopy(text: string, index: number) {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  }

  function handleExportChat() {
    const transcript = messages
      .map((m) => `### ${m.role === "user" ? "Candidate" : "Career Copilot"}\n\n${m.text}\n`)
      .join("\n---\n\n");
    const blob = new Blob([`# RoleRadar Career Copilot Conversation\n\n${transcript}`], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `roleradar_copilot_chat_${new Date().toISOString().slice(0, 10)}.md`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="max-w-3xl flex flex-col h-[calc(100vh-5.5rem)]">
      {/* Header Bar */}
      <div className="mb-3 shrink-0 bg-white p-4 rounded-xl border border-ink-100 shadow-xs flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-signal-500/10 flex items-center justify-center text-signal-600">
            <Bot size={20} />
          </div>
          <div>
            <h1 className="font-display text-lg text-ink-900 leading-tight">Career Copilot</h1>
            <p className="text-[11px] text-ink-500">Grounded career strategist for resume, matches & interview prep</p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-1.5">
          <button
            onClick={handleExportChat}
            className="flex items-center gap-1 text-xs text-ink-600 hover:text-ink-900 transition-colors px-2.5 py-1 rounded-md bg-ink-50 hover:bg-ink-100"
            title="Export conversation as Markdown"
          >
            <Download size={13} /> Export
          </button>
          <button
            onClick={() => clear.mutate()}
            disabled={clear.isPending}
            className="flex items-center gap-1 text-xs text-ink-500 hover:text-alert-600 transition-colors px-2.5 py-1 rounded-md bg-ink-50 hover:bg-alert-600/10"
            title="Clear chat history"
          >
            <Trash2 size={13} /> Clear
          </button>
        </div>
      </div>

      {/* Message Stream */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-3 pr-2 min-h-0">
        {isLoading && <p className="text-xs text-ink-400">Loading conversation…</p>}

        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`group relative max-w-xl rounded-xl p-4 text-xs shadow-xs transition-all ${
                m.role === "user"
                  ? "bg-ink-950 text-white rounded-br-none"
                  : "bg-white border border-ink-100 text-ink-800 rounded-bl-none"
              }`}
            >
              {m.role === "user" ? (
                <p className="whitespace-pre-wrap font-medium">{m.text}</p>
              ) : (
                <>
                  <FormattedMarkdown content={m.text} />
                  {/* Copy Button */}
                  <div className="mt-2.5 pt-2 border-t border-ink-50 flex items-center justify-between opacity-70 group-hover:opacity-100 transition-opacity">
                    <span className="text-[10px] text-ink-400">Grounded Career Advisor</span>
                    <button
                      onClick={() => handleCopy(m.text, i)}
                      className="inline-flex items-center gap-1 text-[11px] text-ink-500 hover:text-signal-700 bg-ink-50 hover:bg-ink-100 px-2 py-0.5 rounded transition-colors"
                    >
                      {copiedIndex === i ? (
                        <>
                          <Check size={11} className="text-signal-600" /> Copied
                        </>
                      ) : (
                        <>
                          <Copy size={11} /> Copy
                        </>
                      )}
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        ))}

        {send.isPending && (
          <div className="flex justify-start">
            <div className="bg-white border border-ink-100 rounded-xl rounded-bl-none p-3.5 text-xs text-ink-600 flex items-center gap-2 shadow-xs">
              <span className="inline-block w-2.5 h-2.5 rounded-full bg-signal-500 animate-pulse" />
              <span>Analyzing your profile and formulating specific recommendations…</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Bar */}
      <div className="shrink-0 bg-white p-2.5 rounded-xl border border-ink-200 shadow-xs">
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
            placeholder="Ask anything (e.g. 'What are my top skill gaps for Backend roles?')"
            className="flex-1 px-3 py-2 text-xs outline-none bg-transparent text-ink-900 placeholder:text-ink-400"
          />
          <button
            onClick={() => handleSend()}
            disabled={send.isPending || !input.trim()}
            className="flex items-center gap-1 rounded-lg bg-ink-950 hover:bg-ink-900 text-white px-4 py-2 text-xs font-semibold transition-all disabled:opacity-40 active:scale-95 shadow-xs"
          >
            <Send size={13} />
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
