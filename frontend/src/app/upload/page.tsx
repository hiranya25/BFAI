"use client";
import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { motion, AnimatePresence } from "framer-motion";
import { UploadCloud, FileType, ShieldAlert, FileText, CheckCircle2, AlertCircle, type LucideIcon } from "lucide-react";

type FileStatus = "idle" | "validating" | "saving" | "parsing" | "classifying" | "indexing" | "indexed" | "error";

interface FileEntry {
  id: string;
  name: string;
  status: FileStatus;
  message?: string;
  docType?: string;
  sensitivity?: string;
  summary?: string;
  pageCount?: number;
}

interface QueuedFile {
  id: string;
  file: File;
}

interface UploadEvent {
  upload_index?: number;
  status: FileStatus;
  doc_type?: string;
  sensitivity?: string;
  summary?: string;
  page_count?: number;
  message?: string;
}

const STATUS_LABELS: Record<FileStatus, string> = {
  idle: "Ready",
  validating: "Validating file signature...",
  saving: "Encrypting and saving...",
  parsing: "Extracting text and tables...",
  classifying: "Llama 3.1 classifying...",
  indexing: "Embedding into ChromaDB...",
  indexed: "Successfully Indexed",
  error: "Upload Failed",
};

function makeId() {
  return crypto.randomUUID?.() ?? Math.random().toString(36).slice(2);
}

export default function UploadPage() {
  const [files, setFiles] = useState<FileEntry[]>([]);
  const [uploading, setUploading] = useState(false);
  const [rawFiles, setRawFiles] = useState<QueuedFile[]>([]);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const updateFile = (id: string, updates: Partial<FileEntry>) => {
    setFiles(prev => prev.map(f => f.id === id ? { ...f, ...updates } : f));
  };

  const onDrop = useCallback((accepted: File[]) => {
    setUploadError(null);
    const queued = accepted.map(file => ({ id: makeId(), file }));
    const entries: FileEntry[] = queued.map(({ id, file }) => ({
      id,
      name: file.name,
      status: "idle",
    }));
    setRawFiles(prev => [...prev, ...queued]);
    setFiles(prev => [...prev, ...entries]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"], "image/*": [".jpg", ".jpeg", ".png"], "text/plain": [".txt"] },
    maxFiles: 10,
  });

  const handleUpload = async () => {
    if (!files.length || uploading) return;
    setUploadError(null);
    setUploading(true);

    const idleFiles = files.filter(f => f.status === "idle");
    const queuedById = new Map(rawFiles.map(item => [item.id, item.file]));
    const payload = idleFiles
      .map((entry, uploadIndex) => ({ entry, file: queuedById.get(entry.id), uploadIndex }))
      .filter((item): item is { entry: FileEntry; file: File; uploadIndex: number } => Boolean(item.file));

    if (!payload.length) {
      setUploadError("No pending files were found to upload.");
      setUploading(false);
      return;
    }

    const formData = new FormData();
    const indexToEntry = new Map<number, FileEntry>();
    payload.forEach(({ entry, file, uploadIndex }) => {
      formData.append("files", file);
      indexToEntry.set(uploadIndex, entry);
    });

    try {
      const response = await fetch(`/api/upload`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        setUploadError(`Upload failed with status ${response.status}.`);
        payload.forEach(({ entry }) => updateFile(entry.id, { status: "error", message: "Upload request failed." }));
        setUploading(false);
        return;
      }

      if (!response.body) {
        setUploadError("Upload response did not include a progress stream.");
        setUploading(false);
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop() ?? "";

        for (const eventText of events) {
          const line = eventText.split("\n").find(l => l.startsWith("data: "));
          if (!line) continue;

          try {
            const event = JSON.parse(line.slice(6)) as UploadEvent;
            const entry = typeof event.upload_index === "number" ? indexToEntry.get(event.upload_index) : undefined;
            if (entry) {
              updateFile(entry.id, {
                status: event.status,
                docType: event.doc_type,
                sensitivity: event.sensitivity,
                summary: event.summary,
                pageCount: event.page_count,
                message: event.message,
              });
            }
          } catch {
            // Ignore malformed SSE frames; the next valid frame will update state.
          }
        }
      }
    } catch {
      setUploadError("Could not reach the backend upload service.");
      payload.forEach(({ entry }) => updateFile(entry.id, { status: "error", message: "Backend unavailable." }));
    }
    setUploading(false);
  };

  return (
    <div className="min-h-screen pt-24 pb-12 px-6">
      <div className="max-w-4xl mx-auto">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-12 text-center">
          <h1 className="text-4xl font-bold text-white mb-4">Knowledge Base</h1>
          <p className="text-slate-400">Upload documents, PDFs, images, and text files to inject knowledge into the agent.</p>
        </motion.div>

        <div
          {...getRootProps()}
          className={`relative overflow-hidden border-2 border-dashed rounded-3xl p-8 sm:p-16 text-center cursor-pointer transition-all duration-300
            ${isDragActive ? "border-indigo-500 bg-indigo-500/10" : "border-white/10 bg-white/[0.02] hover:bg-white/[0.05]"}`}
        >
          <input {...getInputProps()} />
          <UploadCloud className={`w-16 h-16 mx-auto mb-6 transition-colors duration-300 ${isDragActive ? "text-indigo-400" : "text-slate-500"}`} />
          <p className="text-lg text-slate-300 font-medium mb-2">
            {isDragActive ? "Drop files to encrypt & upload" : "Drag & drop files here"}
          </p>
          <p className="text-sm text-slate-500">Supports PDF, TXT, JPG, PNG up to 20MB</p>
          
          <AnimatePresence>
            {isDragActive && (
              <motion.div
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="absolute inset-0 bg-indigo-500/20 blur-[100px] pointer-events-none"
              />
            )}
          </AnimatePresence>
        </div>

        <div className="mt-8 space-y-4">
          {uploadError && (
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-sm text-rose-300">
              {uploadError}
            </div>
          )}
          <AnimatePresence>
            {files.map((f, i) => (
              <motion.div
                key={f.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
                className="p-6 rounded-2xl bg-white/[0.03] border border-white/10 backdrop-blur-xl relative overflow-hidden"
              >
                <div className="flex items-center justify-between gap-4 mb-4">
                  <div className="flex min-w-0 items-center gap-3">
                    <FileText className="w-5 h-5 text-indigo-400 shrink-0" />
                    <span className="font-medium text-white truncate">{f.name}</span>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    {f.status === "indexed" && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
                    {f.status === "error" && <AlertCircle className="w-4 h-4 text-rose-400" />}
                    <span className={`text-sm font-medium ${f.status === "error" ? "text-rose-400" : f.status === "indexed" ? "text-emerald-400" : "text-indigo-400"}`}>
                      {STATUS_LABELS[f.status]}
                    </span>
                  </div>
                </div>

                <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                  <motion.div
                    className={`h-full rounded-full ${f.status === "error" ? "bg-rose-500" : "bg-indigo-500"}`}
                    initial={{ width: "0%" }}
                    animate={{ width: progressWidth(f.status) }}
                    transition={{ type: "spring", bounce: 0, duration: 0.8 }}
                  />
                </div>

                <AnimatePresence>
                  {f.status === "indexed" && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }}
                      className="mt-6 pt-4 border-t border-white/10"
                    >
                      <p className="text-sm text-slate-300 leading-relaxed mb-4">{f.summary}</p>
                      <div className="flex flex-wrap gap-2">
                        <Badge icon={FileType} label={f.docType || "Unknown"} color="indigo" />
                        <Badge icon={ShieldAlert} label={f.sensitivity || "Unknown"} color={f.sensitivity === "confidential" || f.sensitivity === "restricted" ? "rose" : "emerald"} />
                        <Badge icon={FileText} label={`${f.pageCount ?? 0} Pages`} color="slate" />
                      </div>
                    </motion.div>
                  )}
                  {f.status === "error" && (
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-4 p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-sm text-rose-400">
                      {f.message}
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>

        <AnimatePresence>
          {files.some(f => f.status === "idle") && (
            <motion.button
              initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }}
              onClick={handleUpload}
              disabled={uploading}
              className="mt-8 w-full py-4 bg-indigo-600 text-white rounded-xl font-semibold shadow-[0_0_40px_rgba(79,70,229,0.3)]
                disabled:opacity-50 disabled:shadow-none hover:bg-indigo-500 transition-all flex justify-center items-center gap-2"
            >
              {uploading ? (
                <><div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Processing...</>
              ) : (
                <><UploadCloud className="w-5 h-5" /> Secure Upload {files.filter(f => f.status === "idle").length} Files</>
              )}
            </motion.button>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

function Badge({ icon: Icon, label, color }: { icon: LucideIcon, label: string, color: "indigo" | "rose" | "emerald" | "slate" }) {
  const colors = {
    indigo: "bg-indigo-500/10 text-indigo-400 border-indigo-500/20",
    rose: "bg-rose-500/10 text-rose-400 border-rose-500/20",
    emerald: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    slate: "bg-white/5 text-slate-400 border-white/10",
  };
  return (
    <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium ${colors[color]}`}>
      <Icon className="w-3.5 h-3.5" />
      {label}
    </div>
  );
}

function progressWidth(status: FileStatus): string {
  const map: Record<FileStatus, string> = {
    idle: "0%", validating: "15%", saving: "30%", parsing: "50%",
    classifying: "70%", indexing: "85%", indexed: "100%", error: "100%",
  };
  return map[status] ?? "0%";
}
