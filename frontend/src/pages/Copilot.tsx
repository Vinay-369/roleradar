import { useEffect, useState, useRef } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bot,
  Trash2,
  Send,
  Sparkles,
  Copy,
  Check,
  Download,
  ArrowRight,
  X,
  Paperclip,
  Mic,
  MicOff,
  Plus,
  MessageSquare,
  FileText,
  Edit2,
  PanelLeftClose,
  PanelLeftOpen,
  Info,
  Layers,
  Share2,
  TriangleAlert,
  RotateCcw,
} from "lucide-react";
import {
  listConversations,
  getConversation,
  createConversation,
  renameConversation,
  deleteConversation,
  sendChatMessage,
  uploadAttachment,
  getChatHistory,
  type ChatMessage,
  type AttachmentPayload,
  type ConversationSummary,
} from "../lib/copilot";
import { useToast } from "../context/ToastContext";

const WELCOME_TEXT = `### Welcome to Career Copilot! 🤖

I am your AI Engineering Mentor and Career Strategist. You can ask me about:
- **Technical & System Design Concepts** (e.g. *Docker vs Kubernetes, Kafka vs RabbitMQ, Database Indexing, Caching*)
- **Algorithms & Coding Strategies** (e.g. *Big-O Notation, Dynamic Programming, Two Pointers, Binary Search*)
- **Interview Questions & STAR Answers** (e.g. *Tell me about yourself, Salary Negotiation, Weakness questions*)
- **Document & Code Review** (Attach any PDF, DOCX, Code file, or text screenshot using the paperclip icon)
- **Resume ATS Audits & Skill Gaps** (e.g. *Optimizing bullet metrics, closing skill gaps for your target role*)

Type any question below or attach a document to begin!`;

const WELCOME: ChatMessage = {
  role: "assistant",
  text: WELCOME_TEXT,
};

function FormattedMarkdown({ content }: { content: string }) {
  const lines = content.split("\n");
  const elements: React.ReactNode[] = [];
  let listItems: string[] = [];
  let codeBlockLines: string[] = [];
  let inCodeBlock = false;
  let codeBlockLang = "";

  function flushList() {
    if (listItems.length > 0) {
      elements.push(
        <ul key={`ul-${elements.length}`} className="my-2.5 list-disc space-y-1.5 pl-5 text-ink-800 marker:text-signal-600 dark:text-slate-200">
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

  function flushCodeBlock() {
    if (codeBlockLines.length > 0 || inCodeBlock) {
      elements.push(
        <div key={`code-${elements.length}`} className="my-3 overflow-hidden rounded-lg border border-slate-700 bg-slate-950 shadow-xs">
          {codeBlockLang && (
            <div className="border-b border-slate-700 bg-slate-900 px-3 py-1 text-[10px] font-mono uppercase tracking-wider text-slate-400">
              {codeBlockLang}
            </div>
          )}
          <pre className="overflow-x-auto p-3 text-xs font-mono leading-relaxed text-emerald-400">
            <code>{codeBlockLines.join("\n")}</code>
          </pre>
        </div>
      );
      codeBlockLines = [];
      inCodeBlock = false;
      codeBlockLang = "";
    }
  }

  function formatInline(text: string): React.ReactNode[] {
    const cleanText = text.replace(/^#{1,6}\s*/, "");
    const parts: React.ReactNode[] = [];
    const regex = /(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)/g;
    let lastIndex = 0;
    let match: RegExpExecArray | null;

    while ((match = regex.exec(cleanText)) !== null) {
      if (match.index > lastIndex) {
        parts.push(cleanText.substring(lastIndex, match.index));
      }
      const token = match[0];
      if (token.startsWith("**") && token.endsWith("**")) {
        parts.push(
          <strong key={`b-${match.index}`} className="font-bold text-ink-950 dark:text-white">
            {token.slice(2, -2)}
          </strong>
        );
      } else if (token.startsWith("`") && token.endsWith("`")) {
        parts.push(
          <code key={`c-${match.index}`} className="rounded border border-slate-200 bg-slate-100 px-1.5 py-0.5 text-[11px] font-mono font-semibold text-signal-700 dark:border-slate-600 dark:bg-slate-700 dark:text-signal-300">
            {token.slice(1, -1)}
          </code>
        );
      } else if (token.startsWith("*") && token.endsWith("*")) {
        parts.push(
          <em key={`i-${match.index}`} className="italic text-ink-700 dark:text-slate-200">
            {token.slice(1, -1)}
          </em>
        );
      }
      lastIndex = match.index + token.length;
    }

    if (lastIndex < cleanText.length) {
      parts.push(cleanText.substring(lastIndex));
    }

    return parts.length > 0 ? parts : [cleanText];
  }

  lines.forEach((line, lineIdx) => {
    const trimmed = line.trim();

    if (trimmed.startsWith("```")) {
      if (inCodeBlock) {
        flushCodeBlock();
      } else {
        flushList();
        inCodeBlock = true;
        codeBlockLang = trimmed.replace(/^```/, "").trim();
      }
      return;
    }

    if (inCodeBlock) {
      codeBlockLines.push(line);
      return;
    }

    // Markdown Headings 1 through 6
    const headingMatch = trimmed.match(/^(#{1,6})\s+(.+)$/);
    if (headingMatch) {
      flushList();
      const level = headingMatch[1].length;
      const headingText = headingMatch[2];
      if (level === 1) {
        elements.push(
          <h1 key={`h1-${lineIdx}`} className="mt-4 mb-2 text-base font-bold text-ink-950 dark:text-white">
            {formatInline(headingText)}
          </h1>
        );
      } else if (level === 2) {
        elements.push(
          <h2 key={`h2-${lineIdx}`} className="mt-3.5 mb-1.5 text-sm font-bold text-ink-950 dark:text-white">
            {formatInline(headingText)}
          </h2>
        );
      } else if (level === 3) {
        elements.push(
          <h3 key={`h3-${lineIdx}`} className="mt-3 mb-1.5 flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-signal-700 dark:text-signal-300">
            <Sparkles size={12} className="text-signal-600 shrink-0" />
            {formatInline(headingText)}
          </h3>
        );
      } else {
        elements.push(
          <h4 key={`h4-${lineIdx}`} className="mt-2.5 mb-1 text-xs font-bold text-ink-900 dark:text-slate-100">
            {formatInline(headingText)}
          </h4>
        );
      }
      return;
    }

    if (trimmed.startsWith("- ") || trimmed.startsWith("* ") || trimmed.startsWith("• ")) {
      listItems.push(trimmed.replace(/^[-*•]\s+/, ""));
    } else if (/^\d+\.\s+/.test(trimmed)) {
      flushList();
      elements.push(
        <div key={`num-${lineIdx}`} className="my-2 flex items-start gap-2.5 text-xs leading-relaxed text-ink-800 dark:text-slate-200">
          <span className="mt-px inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-amber-200 bg-amber-100 text-[10px] font-bold text-amber-800 dark:border-amber-800 dark:bg-amber-900/60 dark:text-amber-200">{trimmed.match(/^\d+/)?.[0]}</span>
          <div>{formatInline(trimmed.replace(/^\d+\.\s+/, ""))}</div>
        </div>
      );
    } else if (trimmed === "") {
      flushList();
    } else {
      flushList();
      elements.push(
        <p key={`p-${lineIdx}`} className="my-2.5 text-xs leading-relaxed text-ink-800 dark:text-slate-200">
          {formatInline(trimmed)}
        </p>
      );
    }
  });

  flushList();
  flushCodeBlock();

  return <div className="space-y-1">{elements}</div>;
}

export function Copilot() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const lastAssistantMsgRef = useRef<HTMLDivElement>(null);
  const isInitialLoadRef = useRef(true);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Multi-session State with localStorage persistence
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(() => {
    try {
      const saved = localStorage.getItem("roleradar_copilot_sidebar_open");
      return saved !== null ? saved === "true" : true;
    } catch {
      return true;
    }
  });
  const [editingConvId, setEditingConvId] = useState<string | null>(null);
  const [editTitleInput, setEditTitleInput] = useState<string>("");

  const toggleSidebar = (open: boolean) => {
    setSidebarOpen(open);
    try {
      localStorage.setItem("roleradar_copilot_sidebar_open", String(open));
    } catch {
      // ignore
    }
  };

  // Chat State & Explicit Generating Guard
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME]);
  const [input, setInput] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const [activeAttachment, setActiveAttachment] = useState<AttachmentPayload | null>(null);
  const [uploadingAttachment, setUploadingAttachment] = useState(false);

  // Share Conversation State
  const [shareModalData, setShareModalData] = useState<{
    id: string;
    title: string;
    messages: ChatMessage[];
  } | null>(null);
  const [shareCopied, setShareCopied] = useState(false);
  const [loadingShareId, setLoadingShareId] = useState<string | null>(null);

  // Voice Input State
  const [isRecording, setIsRecording] = useState(false);
  const recognitionRef = useRef<any>(null);

  // Navigation Context Focus
  const urlPrompt = searchParams.get("prompt");
  const urlRole = searchParams.get("role");
  const urlCompany = searchParams.get("company");
  const urlCategory = searchParams.get("category");

  const [activeContext, setActiveContext] = useState<{ role?: string; company?: string; category?: string } | null>(
    urlRole || urlCompany ? { role: urlRole || undefined, company: urlCompany || undefined, category: urlCategory || undefined } : null
  );

  const isSendingRef = useRef(false);
  const justReceivedReplyRef = useRef(false);
  const autoSentPromptRef = useRef<string | null>(null);

  // Queries
  const { data: conversations, isLoading: loadingConversations } = useQuery({
    queryKey: ["copilot-conversations"],
    queryFn: listConversations,
  });

  const { data: legacyHistory } = useQuery({
    queryKey: ["copilot-history"],
    queryFn: () => getChatHistory(),
    enabled: !activeConvId,
  });

  const { data: activeConvData } = useQuery({
    queryKey: ["copilot-conversation", activeConvId],
    queryFn: () => (activeConvId ? getConversation(activeConvId) : null),
    enabled: !!activeConvId,
  });

  // Sync messages with loaded conversation (only when not currently generating an answer in-flight and not handling a URL prompt)
  useEffect(() => {
    if (!isGenerating && !urlPrompt) {
      if (activeConvData) {
        setMessages(activeConvData.messages.length > 0 ? activeConvData.messages : [WELCOME]);
      } else if (!activeConvId && legacyHistory && legacyHistory.length > 0) {
        setMessages(legacyHistory);
      }
    }
  }, [activeConvData, legacyHistory, activeConvId, isGenerating, urlPrompt]);

  // Set initial active conversation if available (only when not loading a URL prompt)
  useEffect(() => {
    if (conversations && conversations.length > 0 && !activeConvId && !urlPrompt && !autoSentPromptRef.current) {
      setActiveConvId(conversations[0].id);
    }
  }, [conversations, activeConvId, urlPrompt]);

  // Intelligent Scroll: only smooth scrolls during active live chat generation, snaps instantly on tab switch/load
  useEffect(() => {
    if (isInitialLoadRef.current) {
      isInitialLoadRef.current = false;
      messagesEndRef.current?.scrollIntoView({ behavior: "instant" as ScrollBehavior });
      return;
    }

    const lastMsg = messages[messages.length - 1];

    if (isSendingRef.current || isGenerating) {
      // User is actively sending a prompt: smoothly track down to typing indicator
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    } else if (justReceivedReplyRef.current && lastMsg?.role === "assistant") {
      // User just received an answer to their prompt: smoothly scroll to top of that reply
      justReceivedReplyRef.current = false;
      lastAssistantMsgRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    } else {
      // When switching conversations in sidebar or switching back to Copilot tab: instant positioning, no smooth scroll animation
      messagesEndRef.current?.scrollIntoView({ behavior: "instant" as ScrollBehavior });
    }
  }, [messages, isGenerating]);

  // Mutations
  const sendMutation = useMutation({
    mutationFn: (payload: { message: string; convId?: string; attachment?: AttachmentPayload }) =>
      sendChatMessage(payload.message, payload.convId, payload.attachment),
    onSuccess: (data) => {
      isSendingRef.current = false;
      justReceivedReplyRef.current = true;
      setIsGenerating(false);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: data.reply,
          grounded: data.grounded,
        },
      ]);
      if (data.conversation_id && data.conversation_id !== activeConvId) {
        setActiveConvId(data.conversation_id);
      }
      queryClient.invalidateQueries({ queryKey: ["copilot-conversations"] });
      if (data.conversation_id) {
        queryClient.invalidateQueries({ queryKey: ["copilot-conversation", data.conversation_id] });
      }
    },
    onError: () => {
      isSendingRef.current = false;
      justReceivedReplyRef.current = true;
      setIsGenerating(false);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: "### Connection Notice\n\nI couldn't process your question right now. Please verify your connection and try again.",
        },
      ]);
    },
    onSettled: () => {
      isSendingRef.current = false;
      setIsGenerating(false);
    },
  });

  const createConvMutation = useMutation({
    mutationFn: (title?: string) => createConversation(title),
    onSuccess: (newConv) => {
      queryClient.invalidateQueries({ queryKey: ["copilot-conversations"] });
      setActiveConvId(newConv.id);
      setMessages([WELCOME]);
      setActiveAttachment(null);
      toast.success("Started a new chat session.");
    },
  });

  const renameConvMutation = useMutation({
    mutationFn: ({ convId, title }: { convId: string; title: string }) => renameConversation(convId, title),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["copilot-conversations"] });
      setEditingConvId(null);
      toast.success("Chat renamed.");
    },
  });

  const deleteConvMutation = useMutation({
    mutationFn: (convId: string) => deleteConversation(convId),
    onSuccess: (_, deletedId) => {
      queryClient.invalidateQueries({ queryKey: ["copilot-conversations"] });
      if (activeConvId === deletedId) {
        setActiveConvId(null);
        setMessages([WELCOME]);
      }
      toast.info("Conversation deleted.");
    },
  });

  function handleSend(textToSend?: string) {
    const query = (textToSend || input).trim();
    if (!query || isSendingRef.current || isGenerating || sendMutation.isPending) return;

    isSendingRef.current = true;
    justReceivedReplyRef.current = false;
    setIsGenerating(true);

    const outgoingAttachment = activeAttachment || undefined;
    const userMsg: ChatMessage = {
      role: "user",
      text: query,
      attachment: outgoingAttachment,
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!textToSend) setInput("");
    setActiveAttachment(null);

    sendMutation.mutate(
      {
        message: query,
        convId: activeConvId || undefined,
        attachment: outgoingAttachment,
      },
      {
        onSettled: () => {
          isSendingRef.current = false;
          setIsGenerating(false);
        },
      }
    );
  }

  function handleRegenerate(index: number) {
    const previousUserMessage = [...messages.slice(0, index)].reverse().find((message) => message.role === "user");
    if (previousUserMessage) handleSend(previousUserMessage.text);
  }

  // Voice Input via Browser Web Speech API
  function toggleVoiceRecording() {
    if (isRecording) {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      setIsRecording(false);
      return;
    }

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      toast.error("Voice input is not supported in this browser. Please use Chrome, Edge, or a Chromium browser.");
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = "en-US";

      recognition.onresult = (event: any) => {
        let transcript = "";
        for (let i = event.resultIndex; i < event.results.length; i++) {
          transcript += event.results[i][0].transcript;
        }
        setInput((prev) => (prev ? `${prev} ${transcript}`.trim() : transcript.trim()));
      };

      recognition.onerror = (err: any) => {
        console.warn("Speech recognition error:", err);
        setIsRecording(false);
        toast.error("Microphone listening stopped.");
      };

      recognition.onend = () => {
        setIsRecording(false);
      };

      recognition.start();
      recognitionRef.current = recognition;
      setIsRecording(true);
      toast.info("Listening... Speak clearly into your microphone.");
    } catch (err) {
      toast.error("Could not access microphone.");
      setIsRecording(false);
    }
  }

  // File Attachment Upload Handler
  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 10 * 1024 * 1024) {
      toast.error("File size exceeds 10MB limit.");
      return;
    }

    setUploadingAttachment(true);
    try {
      const res = await uploadAttachment(file);
      setActiveAttachment({
        filename: res.filename,
        file_type: res.file_type,
        extracted_text: res.extracted_text,
        file_data: res.file_data,
        is_resume: res.is_resume,
      });

      if (res.is_resume) {
        toast.success(`Attached ${res.filename} (Resume structure detected).`);
      } else {
        toast.success(`Attached ${res.filename} (${res.char_count} characters extracted).`);
      }
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Failed to process attachment.");
    } finally {
      setUploadingAttachment(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  // Auto-send URL prompt if passed (e.g. from Jobs, Internships, or Interview prep)
  useEffect(() => {
    if (urlPrompt && autoSentPromptRef.current !== urlPrompt) {
      autoSentPromptRef.current = urlPrompt;

      const newContext =
        urlRole || urlCompany || urlCategory
          ? { role: urlRole || undefined, company: urlCompany || undefined, category: urlCategory || undefined }
          : null;
      setActiveContext(newContext);

      // Clean search params using React Router's setSearchParams
      setSearchParams({}, { replace: true });

      // Start a fresh focused thread directly
      setActiveConvId(null);
      isSendingRef.current = true;
      justReceivedReplyRef.current = false;
      setIsGenerating(true);

      const userMsg: ChatMessage = {
        role: "user",
        text: urlPrompt,
      };
      setMessages([WELCOME, userMsg]);
      setInput("");
      setActiveAttachment(null);

      sendMutation.mutate({
        message: urlPrompt,
        convId: undefined,
      });
    }
  }, [urlPrompt, urlRole, urlCompany, urlCategory, setSearchParams]);

  function handleCopy(text: string, index: number) {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    toast.success("Copied to clipboard!");
    setTimeout(() => setCopiedIndex(null), 2000);
  }

  function getShareableTranscript(title: string, msgs: ChatMessage[]) {
    const formattedMsgs = msgs
      .map((m) => {
        const sender = m.role === "user" ? "Candidate" : "RoleRadar Career Copilot";
        return `### ${sender}\n\n${m.text}\n`;
      })
      .join("\n---\n\n");

    return `# ${title}\n*Exported from RoleRadar Career Copilot on ${new Date().toLocaleDateString()}*\n\n---\n\n${formattedMsgs}`;
  }

  async function handleOpenShare(convId?: string, convTitle?: string) {
    const targetId = convId || activeConvId;
    const targetTitle = convTitle || conversations?.find((c) => c.id === targetId)?.title || "Career Copilot Conversation";

    if (targetId && targetId === activeConvId && messages.length > 0) {
      setShareModalData({
        id: targetId,
        title: targetTitle,
        messages: messages,
      });
      return;
    }

    if (targetId) {
      setLoadingShareId(targetId);
      try {
        const data = await getConversation(targetId);
        setShareModalData({
          id: targetId,
          title: data.title || targetTitle,
          messages: data.messages.length > 0 ? data.messages : [WELCOME],
        });
      } catch {
        toast.error("Failed to load conversation for sharing.");
      } finally {
        setLoadingShareId(null);
      }
    } else {
      setShareModalData({
        id: "current",
        title: "Career Copilot Conversation",
        messages: messages,
      });
    }
  }

  async function handleCopyTranscript() {
    if (!shareModalData) return;
    const transcript = getShareableTranscript(shareModalData.title, shareModalData.messages);
    await navigator.clipboard.writeText(transcript);
    setShareCopied(true);
    toast.success("Conversation transcript copied to clipboard!");
    setTimeout(() => setShareCopied(false), 2000);
  }

  async function handleNativeShare() {
    if (!shareModalData) return;
    const transcript = getShareableTranscript(shareModalData.title, shareModalData.messages);
    if (navigator.share) {
      try {
        await navigator.share({
          title: shareModalData.title,
          text: transcript,
        });
        toast.success("Shared successfully!");
      } catch (err: any) {
        if (err?.name !== "AbortError") {
          await handleCopyTranscript();
        }
      }
    } else {
      await handleCopyTranscript();
    }
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
    toast.success("Chat conversation exported as Markdown.");
  }

  return (
    <div className="flex h-full w-full select-text overflow-hidden bg-slate-50 dark:bg-slate-950">
      {/* ------------------------------------------------------------------ */}
      {/* Left Sidebar: Multi-Session Conversation Threads */}
      {/* ------------------------------------------------------------------ */}
      <div
        className={`z-10 flex h-full shrink-0 flex-col overflow-hidden border-r border-slate-200 bg-white shadow-xs transition-all duration-300 dark:border-slate-800 dark:bg-slate-900 ${
          sidebarOpen ? "w-64 sm:w-72" : "w-0 p-0 border-0 overflow-hidden"
        }`}
      >
        {sidebarOpen && (
          <>
            {/* Sidebar Header */}
            <div className="flex shrink-0 items-center justify-between border-b border-slate-200 bg-slate-50 p-3 dark:border-slate-800 dark:bg-slate-900">
              <div className="flex items-center gap-2">
                <MessageSquare size={15} className="text-signal-600" />
                <h2 className="text-xs font-bold uppercase tracking-wider text-ink-900 dark:text-slate-100">Conversations</h2>
              </div>
              <button
                onClick={() => toggleSidebar(false)}
                className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-ink-400 transition-colors hover:bg-slate-200 hover:text-ink-700 dark:hover:bg-slate-800 dark:hover:text-white"
                title="Collapse sidebar"
                aria-label="Collapse sidebar"
              >
                <PanelLeftClose size={15} />
              </button>
            </div>

            {/* New Chat Button */}
            <div className="shrink-0 border-b border-slate-200 p-2.5 dark:border-slate-800">
              <button
                onClick={() => createConvMutation.mutate(undefined)}
                disabled={createConvMutation.isPending}
                className="flex w-full items-center justify-center gap-2 rounded-xl bg-signal-600 px-3 py-2 text-xs font-bold text-white shadow-2xs transition-all hover:bg-signal-700 active:scale-95 disabled:opacity-50"
              >
                <Plus size={14} />
                <span>New Chat</span>
              </button>
            </div>

            {/* Conversation Threads List */}
            <div className="flex-1 overflow-y-auto p-2 space-y-1">
              {loadingConversations && (
                <p className="text-xs text-ink-400 p-3 text-center">Loading threads…</p>
              )}

              {conversations && conversations.length === 0 && (
                <p className="text-xs text-ink-400 p-4 text-center">No past chats yet. Start a new conversation!</p>
              )}

              {conversations?.map((conv: ConversationSummary) => {
                const isActive = conv.id === activeConvId;
                const isEditing = conv.id === editingConvId;

                return (
                  <div
                    key={conv.id}
                    className={`group relative rounded-xl p-2.5 transition-all text-left flex items-center justify-between gap-1.5 cursor-pointer ${
                      isActive
                        ? "bg-signal-500/10 border border-signal-500/30 text-signal-950 font-semibold"
                        : "hover:bg-ink-50 text-ink-700 border border-transparent"
                    }`}
                    onClick={() => {
                      if (!isEditing) setActiveConvId(conv.id);
                    }}
                  >
                    <div className="min-w-0 flex-1">
                      {isEditing ? (
                        <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                          <input
                            value={editTitleInput}
                            onChange={(e) => setEditTitleInput(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") renameConvMutation.mutate({ convId: conv.id, title: editTitleInput });
                              if (e.key === "Escape") setEditingConvId(null);
                            }}
                            autoFocus
                            className="w-full px-1.5 py-0.5 text-xs rounded border border-signal-500 bg-white text-ink-900 outline-none"
                          />
                          <button
                            onClick={() => renameConvMutation.mutate({ convId: conv.id, title: editTitleInput })}
                            className="p-1 rounded text-signal-600 hover:bg-signal-50"
                          >
                            <Check size={12} />
                          </button>
                        </div>
                      ) : (
                        <>
                          <p className="text-xs truncate font-medium">{conv.title}</p>
                          {conv.last_preview && (
                            <p className="text-[10px] text-ink-400 truncate mt-0.5">{conv.last_preview}</p>
                          )}
                        </>
                      )}
                    </div>

                    {!isEditing && (
                      <div className="flex items-center opacity-0 group-hover:opacity-100 transition-opacity gap-0.5">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleOpenShare(conv.id, conv.title);
                          }}
                          disabled={loadingShareId === conv.id}
                          className="p-1 rounded text-ink-400 hover:text-signal-600 hover:bg-signal-50 transition-colors"
                          title="Share conversation"
                          aria-label="Share conversation"
                        >
                          <Share2 size={12} />
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setEditingConvId(conv.id);
                            setEditTitleInput(conv.title);
                          }}
                          className="p-1 rounded text-ink-400 hover:text-ink-800 hover:bg-ink-100 transition-colors"
                          title="Rename"
                          aria-label="Rename conversation"
                        >
                          <Edit2 size={12} />
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteConvMutation.mutate(conv.id);
                          }}
                          className="p-1 rounded text-ink-400 hover:text-alert-600 hover:bg-alert-50 transition-colors"
                          title="Delete"
                          aria-label="Delete conversation"
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Main Chat Workspace (Full-Height ChatGPT/Claude Style Layout) */}
      {/* ------------------------------------------------------------------ */}
      <div className="flex h-full min-w-0 flex-1 flex-col overflow-hidden bg-white dark:bg-slate-900">
        {/* Sleek Compact Header Bar */}
        <header className="min-h-14 px-3 sm:px-6 border-b border-slate-200 bg-white/95 backdrop-blur-sm flex items-center justify-between gap-3 shrink-0 z-10 dark:border-slate-800 dark:bg-slate-900/95">
          <div className="flex items-center gap-2.5 min-w-0">
            <button
              onClick={() => toggleSidebar(!sidebarOpen)}
              className="inline-flex h-9 w-9 items-center justify-center rounded-lg text-ink-500 transition-colors hover:bg-slate-100 hover:text-ink-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-white"
              title={sidebarOpen ? "Collapse conversation sidebar" : "Open conversation sidebar"}
              aria-label={sidebarOpen ? "Collapse conversation sidebar" : "Open conversation sidebar"}
            >
              {sidebarOpen ? <PanelLeftClose size={16} /> : <PanelLeftOpen size={16} />}
            </button>

            <div className="w-8 h-8 rounded-lg bg-signal-500/10 text-signal-700 flex items-center justify-center shrink-0 font-bold border border-signal-500/20 dark:text-signal-300">
              <Bot size={15} />
            </div>

            <div className="flex min-w-0 flex-col gap-0.5 sm:flex-row sm:items-center sm:gap-2">
              <h1 className="font-display text-sm font-bold text-ink-950 truncate dark:text-white">
                Career Copilot
              </h1>
              <span className="inline-flex w-fit items-center rounded-full border border-signal-200 bg-signal-50 px-2 py-0.5 text-[9px] font-semibold text-signal-700 dark:border-signal-900 dark:bg-signal-950/50 dark:text-signal-300">
                Engineering Mentor v4
              </span>
            </div>
          </div>

          {/* Top Actions */}
          <div className="flex shrink-0 items-center gap-1 rounded-xl border border-slate-200 bg-slate-50 p-1 dark:border-slate-700 dark:bg-slate-800">
            <button
              onClick={() => handleOpenShare()}
              className="inline-flex h-8 items-center gap-1.5 rounded-lg px-2.5 text-xs font-semibold text-ink-600 transition-colors hover:bg-white hover:text-signal-700 dark:text-slate-300 dark:hover:bg-slate-700 dark:hover:text-white"
              title="Share this chat history"
            >
              <Share2 size={12} />
              <span className="hidden sm:inline">Share</span>
            </button>

            <button
              onClick={handleExportChat}
              className="inline-flex h-8 items-center gap-1.5 rounded-lg px-2.5 text-xs font-semibold text-ink-600 transition-colors hover:bg-white hover:text-ink-950 dark:text-slate-300 dark:hover:bg-slate-700 dark:hover:text-white"
              title="Export conversation as Markdown"
            >
              <Download size={12} />
              <span className="hidden md:inline">Export</span>
            </button>

            <button
              onClick={() => createConvMutation.mutate(undefined)}
              disabled={createConvMutation.isPending}
              className="inline-flex h-8 items-center gap-1 rounded-lg bg-signal-600 px-2.5 text-xs font-bold text-white shadow-xs transition-colors hover:bg-signal-700 active:scale-95 disabled:opacity-60 sm:gap-1.5 sm:px-3"
              title="Start a new chat"
            >
              <Plus size={13} />
              <span className="hidden sm:inline">New Chat</span>
            </button>
          </div>
        </header>

        {/* Dynamic Context Banner */}
        {activeContext && (
          <div className="flex shrink-0 items-center justify-between border-b border-signal-500/20 bg-gradient-to-r from-signal-500/10 via-signal-500/5 to-transparent px-4 py-2 text-xs text-ink-800 dark:text-slate-200 sm:px-6">
            <div className="flex items-center gap-2">
              <Layers size={13} className="text-signal-600 shrink-0" />
              <span>
                <strong>Context Focused:</strong> Analyzing for{" "}
                <span className="font-semibold text-signal-700 dark:text-signal-300">{activeContext.role || "Target Role"}</span>
                {activeContext.company ? ` at ${activeContext.company}` : ""}
              </span>
            </div>
            <button
              onClick={() => setActiveContext(null)}
              className="rounded p-1 text-ink-400 transition-colors hover:text-ink-700 dark:hover:text-white"
              title="Dismiss focused context"
            >
              <X size={12} />
            </button>
          </div>
        )}

        {/* Expansive Message Stream */}
        <div className="flex-1 snap-y snap-proximity overflow-y-auto bg-slate-50/60 px-3 py-5 sm:px-8 sm:py-6 dark:bg-slate-950/40">
          <div className="max-w-4xl mx-auto space-y-4">
            {messages.map((m, i) => (
              <div
                key={i}
                ref={i === messages.length - 1 && m.role === "assistant" ? lastAssistantMsgRef : null}
                className={`flex snap-start ${m.role === "user" ? "justify-end pl-8 sm:pl-16" : "justify-start pr-2"} animate-fade-in-up`}
              >
                {m.role === "user" ? (
                  <div className="max-w-xl w-fit rounded-2xl rounded-br-sm border border-slate-700 bg-slate-900 px-3.5 py-2.5 text-xs leading-relaxed text-white shadow-sm sm:px-4 sm:py-3 dark:border-slate-700 dark:bg-slate-800">
                    {m.attachment && (
                      <div className="mb-2 p-2 rounded-xl bg-ink-900 border border-ink-800 flex items-center justify-between text-[11px] text-ink-200 gap-2">
                        <div className="flex items-center gap-1.5 truncate">
                          <Paperclip size={12} className="text-signal-400 shrink-0" />
                          <span className="truncate font-medium text-ink-100">{m.attachment.filename}</span>
                        </div>
                        <span className="text-[9px] uppercase tracking-wider text-ink-400 font-mono bg-ink-950 px-1.5 py-0.5 rounded border border-ink-800 shrink-0">
                          {m.attachment.file_type}
                        </span>
                      </div>
                    )}
                    <p className="whitespace-pre-wrap font-medium">{m.text}</p>
                  </div>
                ) : (
                  <div className={`w-full max-w-4xl rounded-2xl rounded-bl-sm border p-4 text-xs leading-relaxed shadow-sm transition-all sm:p-5 ${
                    m.text.toLowerCase().includes("local ai connection notice")
                      ? "border-amber-200 bg-amber-50 text-amber-950 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-100"
                      : "border-slate-200 bg-white text-ink-800 dark:border-slate-800 dark:bg-slate-800 dark:text-slate-100"
                  }`}>
                    {m.text.toLowerCase().includes("local ai connection notice") && (
                      <div className="mb-3 flex items-start gap-2.5 border-b border-amber-200/80 pb-3 dark:border-amber-800/70">
                        <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-amber-100 text-amber-700 dark:bg-amber-900/60 dark:text-amber-300">
                          <TriangleAlert size={17} />
                        </span>
                        <div>
                          <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-amber-700 dark:text-amber-300">Local AI connection notice</p>
                          <p className="mt-1 text-xs font-medium text-amber-950 dark:text-amber-100">Career Copilot could not reach the local Ollama model.</p>
                        </div>
                      </div>
                    )}
                    <FormattedMarkdown content={m.text.replace(/^###\s*⚠️?\s*Local AI Connection Notice\s*/i, "")} />

                    {/* Proactive Resume Intelligence Suggestion Card */}
                    {m.resume_suggestion && (
                      <div className="mt-3.5 flex items-center justify-between gap-2 rounded-xl border border-signal-500/30 bg-signal-500/10 p-2.5 dark:bg-signal-950/40">
                        <div className="flex items-center gap-2">
                          <Sparkles size={14} className="text-signal-600 shrink-0" />
                          <span className="text-[11px] font-medium text-signal-950 dark:text-signal-100">
                            {m.resume_suggestion}
                          </span>
                        </div>
                        <Link
                          to="/resume/master"
                          className="shrink-0 px-2.5 py-1 rounded-lg bg-signal-600 hover:bg-signal-700 text-white text-[11px] font-bold shadow-2xs transition-colors flex items-center gap-1"
                        >
                          Upload to Master <ArrowRight size={11} />
                        </Link>
                      </div>
                    )}

                    {/* Copy Button Footer */}
                    <div className="mt-4 flex items-center justify-between gap-2 border-t border-slate-200/80 pt-3 dark:border-slate-700">
                      <span className="text-[10px] font-semibold text-ink-400 dark:text-slate-400">RoleRadar Grounded Mentor</span>
                      <div className="flex items-center gap-1.5">
                        {i > 0 && messages.slice(0, i).some((message) => message.role === "user") && (
                          <button
                            onClick={() => handleRegenerate(i)}
                            disabled={isGenerating || sendMutation.isPending}
                            className="inline-flex h-7 items-center gap-1 rounded-lg border border-slate-200 bg-white px-2 text-[11px] font-medium text-ink-600 transition-colors hover:bg-slate-50 hover:text-signal-700 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700 dark:hover:text-white"
                          >
                            <RotateCcw size={11} /> Regenerate
                          </button>
                        )}
                        <button
                          onClick={() => handleCopy(m.text, i)}
                          className="inline-flex h-7 items-center gap-1 rounded-lg border border-slate-200 bg-white px-2 text-[11px] font-medium text-ink-600 transition-colors hover:bg-slate-50 hover:text-signal-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700 dark:hover:text-white"
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
                    </div>
                  </div>
                )}
              </div>
            ))}

            {(isGenerating || sendMutation.isPending) && messages[messages.length - 1]?.role === "user" && (
              <div className="flex justify-start animate-fade-in-up">
                <div className="flex items-center gap-1.5 rounded-2xl rounded-bl-sm border border-slate-200 bg-white px-4 py-3 text-xs text-ink-600 shadow-xs dark:border-slate-800 dark:bg-slate-800 dark:text-slate-300">
                  <span className="w-2 h-2 rounded-full bg-signal-500 animate-bounce" style={{ animationDelay: "0ms" }} />
                  <span className="w-2 h-2 rounded-full bg-signal-500 animate-bounce" style={{ animationDelay: "150ms" }} />
                  <span className="w-2 h-2 rounded-full bg-signal-500 animate-bounce" style={{ animationDelay: "300ms" }} />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* ------------------------------------------------------------------ */}
        {/* Streamlined Bottom Input Dock */}
        {/* ------------------------------------------------------------------ */}
        <div className="shrink-0 border-t border-slate-200 bg-white/95 px-3 pt-2.5 pb-3.5 backdrop-blur-sm dark:border-slate-800 dark:bg-slate-900/95 sm:px-8">
          <div className="max-w-4xl mx-auto space-y-2">

            {/* Active Attachment Chip (When attached before sending) */}
            {activeAttachment && (
              <div className="flex items-center justify-between gap-2 rounded-xl border border-teal-200 bg-teal-50 p-2.5 text-xs text-teal-950 animate-fade-in-up dark:border-teal-900 dark:bg-teal-950/40 dark:text-teal-100">
                <div className="flex items-center gap-2 min-w-0">
                  <FileText size={15} className="text-teal-700 shrink-0" />
                  <span className="font-semibold truncate">{activeAttachment.filename}</span>
                  <span className="rounded border border-teal-200 bg-white px-2 py-0.5 text-[10px] font-mono text-teal-700 dark:border-teal-800 dark:bg-slate-900 dark:text-teal-300">
                    {activeAttachment.file_type} • {activeAttachment.extracted_text.length} chars
                  </span>
                  {activeAttachment.is_resume && (
                    <span className="rounded bg-emerald-100 px-2 py-0.5 text-[10px] font-bold text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">
                      ✓ Resume Detected
                    </span>
                  )}
                </div>
                <button
                  type="button"
                  onClick={() => setActiveAttachment(null)}
                  className="text-teal-700 hover:text-alert-600 p-1 rounded transition-colors"
                  title="Remove attachment"
                >
                  <X size={14} />
                </button>
              </div>
            )}

            {/* Main Input Bar */}
            <div className="flex items-center gap-1.5 rounded-2xl border border-slate-200 bg-white p-2 shadow-sm transition-all focus-within:border-signal-500 focus-within:ring-2 focus-within:ring-signal-500/10 dark:border-slate-700 dark:bg-slate-900 sm:gap-2 sm:p-2.5">
              {/* Hidden File Input */}
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileUpload}
                accept=".pdf,.docx,.doc,.txt,.md,.py,.ts,.js,.json,.csv,.sql,.png,.jpg,.jpeg,.webp"
                className="hidden"
              />

              {/* Attach File Button */}
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploadingAttachment}
                className={`shrink-0 rounded-xl p-2 text-ink-500 transition-colors hover:bg-slate-100 hover:text-ink-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-white ${
                  activeAttachment ? "bg-teal-50 text-teal-600 dark:bg-teal-950/50 dark:text-teal-300" : ""
                }`}
                title="Attach Document (PDF, DOCX, Code, TXT) or Screenshot"
              >
                {uploadingAttachment ? (
                  <span className="w-4 h-4 rounded-full border-2 border-signal-600 border-t-transparent animate-spin block" />
                ) : (
                  <Paperclip size={16} />
                )}
              </button>

              {/* Voice Input Microphone Button */}
              <button
                type="button"
                onClick={toggleVoiceRecording}
                className={`p-2 rounded-xl transition-all shrink-0 ${
                  isRecording
                    ? "bg-alert-600 text-white shadow-xs animate-pulse"
                    : "text-ink-500 hover:bg-slate-100 hover:text-ink-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-white"
                }`}
                title={isRecording ? "Stop voice listening" : "Voice input (Speech to Text)"}
              >
                {isRecording ? <MicOff size={16} /> : <Mic size={16} />}
              </button>

              {/* Main Text Input */}
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
                placeholder={
                  isRecording
                    ? "Listening... Speak clearly to dictate your message..."
                    : activeAttachment
                    ? `Ask questions about ${activeAttachment.filename}…`
                    : "Ask anything about system design, coding, interview strategy, or resume metrics…"
                }
                className="min-w-0 flex-1 bg-transparent px-2 py-2 text-xs text-ink-900 outline-none placeholder:text-ink-400 dark:text-white dark:placeholder:text-slate-500 sm:text-sm"
              />

              {/* Send Button */}
              <button
                onClick={() => handleSend()}
                disabled={isGenerating || sendMutation.isPending || (!input.trim() && !activeAttachment)}
                className={`inline-flex h-10 shrink-0 items-center justify-center gap-1.5 rounded-xl px-3 text-xs font-semibold text-white shadow-xs transition-all active:scale-95 disabled:cursor-not-allowed disabled:opacity-45 sm:px-4 ${
                  input.trim() || activeAttachment
                    ? "bg-signal-600 hover:bg-signal-700"
                    : "bg-slate-400 dark:bg-slate-700"
                }`}
              >
                <Send size={13} />
                <span>Send</span>
              </button>
            </div>

            {/* Transparent OCR / Limitation Note Footer */}
            <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-1 px-2 text-center text-[10px] text-ink-400 dark:text-slate-500">
              <span className="flex items-center gap-1">
                <Info size={10} className="text-ink-400 shrink-0" />
                Attachments extract text via OCR. Photos/diagrams are text-extracted only.
              </span>
              <span className="font-mono hidden sm:inline">Press Enter to send</span>
            </div>
          </div>
        </div>
      </div>

      {/* Share Conversation Modal */}
      {shareModalData && (
        <div
          className="fixed inset-0 bg-ink-950/50 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-fade-in"
          onClick={() => setShareModalData(null)}
        >
          <div
            className="w-full max-w-md bg-white rounded-2xl border border-ink-100 p-5 shadow-2xl space-y-4 animate-scale-in"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-2.5">
                <span className="p-2 rounded-xl bg-signal-500/10 text-signal-700">
                  <Share2 size={18} />
                </span>
                <div>
                  <h3 className="text-sm font-bold text-ink-950">Share Chat History</h3>
                  <p className="text-xs text-ink-500">Copy or share this conversation</p>
                </div>
              </div>
              <button
                onClick={() => setShareModalData(null)}
                className="p-1 rounded-lg text-ink-400 hover:text-ink-800 hover:bg-ink-100 transition-colors"
                aria-label="Close"
              >
                <X size={16} />
              </button>
            </div>

            {/* Conversation Summary Box */}
            <div className="p-3.5 rounded-xl bg-ink-50 border border-ink-100 space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-ink-900 truncate max-w-[280px]">
                  {shareModalData.title}
                </span>
                <span className="text-[11px] font-medium text-ink-500 shrink-0">
                  {shareModalData.messages.length} {shareModalData.messages.length === 1 ? "msg" : "msgs"}
                </span>
              </div>
              <p className="text-[11px] text-ink-600 line-clamp-2 italic">
                &ldquo;{shareModalData.messages[shareModalData.messages.length - 1]?.text.slice(0, 140)}…&rdquo;
              </p>
            </div>

            {/* Actions Grid */}
            <div className="grid grid-cols-2 gap-2 pt-1">
              <button
                onClick={handleCopyTranscript}
                className="flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl bg-signal-500 hover:bg-signal-600 text-white text-xs font-bold shadow-xs transition-all active:scale-95 cursor-pointer"
              >
                {shareCopied ? (
                  <>
                    <Check size={14} />
                    <span>Copied!</span>
                  </>
                ) : (
                  <>
                    <Copy size={14} />
                    <span>Copy Transcript</span>
                  </>
                )}
              </button>

              <button
                onClick={handleNativeShare}
                className="flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl bg-ink-950 hover:bg-ink-900 text-white text-xs font-bold shadow-xs transition-all active:scale-95 cursor-pointer"
              >
                <Share2 size={14} />
                <span>Share via App</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
