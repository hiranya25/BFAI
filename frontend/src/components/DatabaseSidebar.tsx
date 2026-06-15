"use client";
import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Database, Trash2, FileText, Loader2, AlertCircle, ShieldAlert } from "lucide-react";

interface DocumentMeta {
  doc_id: string;
  filename: string;
  doc_type: string;
  sensitivity: string;
  page_count: number;
  chunk_count: number;
}

export function DatabaseSidebar({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const [documents, setDocuments] = useState<DocumentMeta[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const fetchDocs = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/documents");
      if (!res.ok) throw new Error("Failed to fetch documents");
      const data = await res.json();
      setDocuments(data.documents);
    } catch (err: any) {
      setError(err.message || "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchDocs();
    }
  }, [isOpen]);

  const handleDelete = async (docId: string) => {
    if (!window.confirm("Are you sure you want to delete this document? This cannot be undone.")) return;
    
    setDeletingId(docId);
    try {
      const res = await fetch(`/api/documents/${docId}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed to delete");
      setDocuments(prev => prev.filter(d => d.doc_id !== docId));
    } catch (err: any) {
      alert(err.message || "Failed to delete document");
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
            onClick={onClose}
          />
          <motion.div
            initial={{ x: "100%" }} animate={{ x: 0 }} exit={{ x: "100%" }}
            transition={{ type: "spring", bounce: 0, duration: 0.4 }}
            className="fixed right-0 top-0 h-full w-[400px] bg-[#0B0F19] border-l border-white/10 shadow-2xl z-50 flex flex-col"
          >
            <div className="p-6 border-b border-white/10 flex items-center justify-between bg-white/[0.02]">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-indigo-500/20 rounded-lg text-indigo-400">
                  <Database className="w-5 h-5" />
                </div>
                <h2 className="text-xl font-semibold text-white">Knowledge Base</h2>
              </div>
              <button onClick={onClose} className="p-2 text-slate-400 hover:text-white hover:bg-white/5 rounded-lg transition">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {loading ? (
                <div className="flex items-center justify-center h-40 text-slate-400">
                  <Loader2 className="w-6 h-6 animate-spin" />
                </div>
              ) : error ? (
                <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-400 flex items-center gap-3">
                  <AlertCircle className="w-5 h-5" />
                  <p className="text-sm">{error}</p>
                </div>
              ) : documents.length === 0 ? (
                <div className="text-center py-12">
                  <Database className="w-12 h-12 text-slate-600 mx-auto mb-4 opacity-50" />
                  <p className="text-slate-400">Your knowledge base is empty.</p>
                </div>
              ) : (
                documents.map(doc => (
                  <div key={doc.doc_id} className="p-4 rounded-xl bg-white/[0.03] border border-white/10 hover:bg-white/[0.05] transition group relative">
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <FileText className="w-4 h-4 text-indigo-400 shrink-0" />
                          <h3 className="font-medium text-white truncate text-sm" title={doc.filename}>{doc.filename}</h3>
                        </div>
                        <div className="flex flex-wrap gap-2 mt-3">
                          <span className="text-[10px] px-2 py-1 rounded-md bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                            {doc.doc_type}
                          </span>
                          <span className="text-[10px] px-2 py-1 rounded-md bg-white/5 text-slate-300 border border-white/10 flex items-center gap-1">
                            {doc.sensitivity === "confidential" ? <ShieldAlert className="w-3 h-3 text-rose-400" /> : null}
                            {doc.sensitivity}
                          </span>
                        </div>
                        <p className="text-xs text-slate-500 mt-3">
                          {doc.page_count} Pages • {doc.chunk_count} Vector Chunks
                        </p>
                      </div>
                      <button
                        onClick={() => handleDelete(doc.doc_id)}
                        disabled={deletingId === doc.doc_id}
                        className="p-2 text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition disabled:opacity-50 shrink-0"
                        title="Delete Document"
                      >
                        {deletingId === doc.doc_id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
