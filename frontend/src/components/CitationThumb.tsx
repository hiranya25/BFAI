import { motion } from "framer-motion";

export interface CitationThumbProps {
  citation: { filename: string; page_num: number; image_path: string };
  onClick: () => void;
}

export function CitationThumb({ citation, onClick }: CitationThumbProps) {
  const imageUrl = `/api/pages/${encodeURIComponent(citation.image_path)}`;

  return (
    <motion.button
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      onClick={onClick}
      className="flex flex-col items-center gap-1 p-2 rounded-xl bg-white/[0.03] border border-white/10
        hover:bg-white/[0.08] hover:border-indigo-500/50 transition-all text-left group"
    >
      <img
        src={imageUrl}
        alt={`Page ${citation.page_num}`}
        className="w-12 h-16 object-cover rounded-md border border-white/10 group-hover:border-indigo-400/50 transition-colors"
        loading="lazy"
      />
      <span className="text-[10px] font-medium text-slate-400 group-hover:text-indigo-300">
        {citation.filename}, p. {citation.page_num}
      </span>
    </motion.button>
  );
}
