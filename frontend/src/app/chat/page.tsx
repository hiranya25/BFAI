"use client";
import { useState, useRef, useEffect } from "react";
import { CitationThumb } from "@/components/CitationThumb";
import { VoiceButton } from "@/components/VoiceButton";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Bot, User, Loader2 } from "lucide-react";

interface Citation { filename: string; page_num: number; image_path: string; }
interface Message {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
}

function getApiConfig() {
  return {};
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([{
    role: "assistant",
    content: "Hi! I'm your Agentic RAG assistant. Ask me anything about the documents you've uploaded to the Knowledge Base."
  }]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [modalImage, setModalImage] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;
    const config = getApiConfig();
    const query = input.trim();
    setInput("");
    setLoading(true);

    const userMsg: Message = { role: "user", content: query };
    setMessages(prev => [...prev, userMsg]);

    if (!config) {
      setMessages(prev => [...prev, {
        role: "assistant",
        content: "Frontend API configuration is missing.",
      }]);
      setLoading(false);
      return;
    }

    try {
      const res = await fetch(`/api/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          messages: messages.map(m => ({ role: m.role, content: m.content })),
          query,
        }),
      });

      if (!res.ok) {
        setMessages(prev => [...prev, {
          role: "assistant",
          content: res.status === 401
            ? "The backend rejected the API key. Check the server API secret."
            : `The backend returned an error (${res.status}).`,
        }]);
        setLoading(false);
        return;
      }

      const data = await res.json();
      setMessages(prev => [...prev, {
        role: "assistant",
        content: data.answer ?? "The backend did not return an answer.",
        citations: data.citations ?? [],
      }]);
    } catch {
      setMessages(prev => [...prev, { role: "assistant", content: "Could not reach the backend agent. Confirm the API server is running." }]);
    }
    setLoading(false);
  };

  return (
    <div className="flex flex-col h-screen pt-16">
      {/* Background Ambient Orbs */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-[10%] left-[20%] w-[40%] h-[40%] bg-indigo-600/10 rounded-full blur-[120px] mix-blend-screen" />
        <div className="absolute bottom-[10%] right-[20%] w-[40%] h-[40%] bg-purple-600/10 rounded-full blur-[120px] mix-blend-screen" />
      </div>

      {/* Message list */}
      <div className="flex-1 overflow-y-auto px-4 py-8 relative z-10 scrollbar-hide">
        <div className="max-w-4xl mx-auto space-y-8">
          <AnimatePresence initial={false}>
            {messages.map((msg, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ type: "spring", stiffness: 400, damping: 30 }}
                className={`flex gap-4 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}
              >
                <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center border ${
                  msg.role === "user" ? "bg-indigo-500/20 border-indigo-500/30 text-indigo-400" : "bg-white/5 border-white/10 text-slate-400"
                }`}>
                  {msg.role === "user" ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
                </div>

                <div className={`max-w-[90%] md:max-w-[80%] flex flex-col gap-2 ${msg.role === "user" ? "items-end" : "items-start"}`}>
                  <div className={`px-5 py-4 rounded-3xl shadow-sm ${
                    msg.role === "user" 
                      ? "bg-gradient-to-tr from-indigo-600 to-indigo-500 text-white rounded-tr-sm" 
                      : "bg-white/[0.03] border border-white/10 backdrop-blur-xl text-slate-300 rounded-tl-sm"
                  }`}>
                    <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                  </div>

                  {/* Citations */}
                  {msg.citations && msg.citations.length > 0 && (
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }} className="mt-2 flex flex-col gap-2">
                      <span className="text-xs font-medium text-slate-500 flex items-center gap-2">
                        <div className="w-4 border-t border-slate-700"></div> SOURCES
                      </span>
                      <div className="flex flex-wrap gap-2">
                        {msg.citations.map((c, j) => (
                          <CitationThumb key={j} citation={c} onClick={() => setModalImage(c.image_path)} />
                        ))}
                      </div>
                    </motion.div>
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {loading && (
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="flex gap-4">
              <div className="flex-shrink-0 w-10 h-10 rounded-full bg-white/5 border border-white/10 flex items-center justify-center text-indigo-400">
                <Loader2 className="w-5 h-5 animate-spin" />
              </div>
              <div className="px-5 py-4 bg-white/[0.03] border border-white/10 backdrop-blur-xl rounded-3xl rounded-tl-sm flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-indigo-500 animate-bounce" />
                <span className="w-2 h-2 rounded-full bg-indigo-500 animate-bounce" style={{ animationDelay: "0.2s" }} />
                <span className="w-2 h-2 rounded-full bg-indigo-500 animate-bounce" style={{ animationDelay: "0.4s" }} />
              </div>
            </motion.div>
          )}
          <div ref={bottomRef} className="h-4" />
        </div>
      </div>

      {/* Input Dock */}
      <div className="p-4 sm:p-6 relative z-10">
        <div className="max-w-3xl mx-auto relative group">
          <div className="absolute -inset-1 bg-gradient-to-r from-indigo-500/20 to-purple-500/20 rounded-3xl blur opacity-0 group-focus-within:opacity-100 transition duration-500" />
          <div className="relative flex items-end gap-3 bg-[#0B0F19] border border-white/10 p-2 rounded-3xl backdrop-blur-xl shadow-2xl">
            <VoiceButton onTranscript={setInput} />
            <textarea
              rows={1}
              className="flex-1 bg-transparent border-none text-slate-200 placeholder:text-slate-600 px-2 py-3 max-h-32 focus:outline-none focus:ring-0 resize-none"
              placeholder="Ask the agent a question..."
              value={input}
              onChange={e => {
                setInput(e.target.value);
                e.target.style.height = 'auto';
                e.target.style.height = e.target.scrollHeight + 'px';
              }}
              onKeyDown={e => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  sendMessage();
                  e.currentTarget.style.height = 'auto';
                }
              }}
            />
            <button
              onClick={sendMessage}
              disabled={loading || !input.trim()}
              className="p-3 bg-indigo-600 text-white rounded-2xl disabled:opacity-40 hover:bg-indigo-500 transition-colors"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      {/* Full-page modal */}
      <AnimatePresence>
        {modalImage && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/90 backdrop-blur-sm z-[100] flex items-center justify-center p-4 sm:p-8"
            onClick={() => setModalImage(null)}
          >
            <motion.img
              initial={{ scale: 0.95 }} animate={{ scale: 1 }} exit={{ scale: 0.95 }} transition={{ type: "spring", bounce: 0 }}
              src={`/api/pages/${encodeURIComponent(modalImage)}`}
              alt="Document page"
              className="max-h-full max-w-full object-contain rounded-2xl shadow-[0_0_100px_rgba(255,255,255,0.1)]"
              onClick={e => e.stopPropagation()}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
