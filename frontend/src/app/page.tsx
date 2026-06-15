"use client";

import { motion } from "framer-motion";
import type { Variants } from "framer-motion";
import Link from "next/link";
import { FileSearch, BrainCircuit, ShieldCheck, Mic, UploadCloud, MessageSquare, type LucideIcon } from "lucide-react";

export default function LandingPage() {
  const containerVariants: Variants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: 0.15 },
    },
  };

  const itemVariants: Variants = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 24 } },
  };

  return (
    <div className="min-h-screen relative overflow-hidden selection:bg-indigo-500/30">
      {/* Background Ambient Orbs */}
      <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-indigo-600/20 rounded-full blur-[120px] mix-blend-screen pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-purple-600/20 rounded-full blur-[120px] mix-blend-screen pointer-events-none" />

      <main className="max-w-7xl mx-auto px-6 pt-32 pb-24 relative z-10">
        {/* HERO SECTION */}
        <motion.div 
          className="text-center max-w-4xl mx-auto mb-32"
          initial="hidden" animate="show" variants={containerVariants}
        >
          <motion.div variants={itemVariants} className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-sm font-medium mb-8">
            <span className="flex h-2 w-2 rounded-full bg-indigo-500 animate-pulse"></span>
            AI Engineer Assessment Project
          </motion.div>
          
          <motion.h1 variants={itemVariants} className="text-5xl md:text-7xl font-extrabold tracking-tight mb-8 leading-tight">
            Document Intelligence, <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-purple-400">
              Reimagined.
            </span>
          </motion.h1>
          
          <motion.p variants={itemVariants} className="text-xl text-slate-400 mb-12 max-w-2xl mx-auto leading-relaxed">
            Upload messy, real-world documents. We extract the text, parse the tables, classify the content, and power an Agentic RAG chatbot that answers questions with exact page-level citations.
          </motion.p>
          
          <motion.div variants={itemVariants} className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link href="/upload" className="w-full sm:w-auto px-8 py-4 bg-white text-slate-900 rounded-xl font-semibold hover:bg-indigo-50 transition-colors flex items-center justify-center gap-2 shadow-[0_0_40px_rgba(99,102,241,0.2)]">
              Start Uploading <UploadCloud className="w-5 h-5" />
            </Link>
            <Link href="/chat" className="w-full sm:w-auto px-8 py-4 bg-white/5 border border-white/10 text-white rounded-xl font-semibold hover:bg-white/10 transition-colors flex items-center justify-center gap-2">
              Talk to Agent <MessageSquare className="w-5 h-5" />
            </Link>
          </motion.div>
        </motion.div>

        {/* FEATURES GRID */}
        <motion.div 
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-32"
          initial="hidden" whileInView="show" viewport={{ once: true, margin: "-100px" }} variants={containerVariants}
        >
          <FeatureCard 
            icon={FileSearch} 
            title="Hybrid Parsing" 
            desc="Intelligently extracts text via marker-pdf and falls back to DocTR for image-heavy scanned reports."
          />
          <FeatureCard 
            icon={BrainCircuit} 
            title="Agentic RAG" 
            desc="Retrieves chunks using vector search and synthesizes highly grounded answers with Groq and Llama 3."
          />
          <FeatureCard 
            icon={ShieldCheck} 
            title="Encrypted Storage" 
            desc="Documents are encrypted at rest using AES-256 and stored with randomized UUIDs to prevent path traversal."
          />
          <FeatureCard 
            icon={Mic} 
            title="Voice Integration" 
            desc="Speak directly to the agent using built-in, real-time browser speech-to-text recognition."
          />
        </motion.div>

        {/* HOW IT WORKS */}
        <motion.div 
          className="max-w-5xl mx-auto"
          initial="hidden" whileInView="show" viewport={{ once: true }} variants={containerVariants}
        >
          <motion.h2 variants={itemVariants} className="text-3xl font-bold text-center mb-16">How it works</motion.h2>
          <div className="grid md:grid-cols-3 gap-8">
            <StepCard number="01" title="Ingest & Parse" desc="Drop your PDFs or images. The backend extracts text, parses tables natively, and renders page thumbnails." />
            <StepCard number="02" title="Classify & Embed" desc="Groq classifies the document type, topic, and sensitivity. Text chunks are embedded into ChromaDB." />
            <StepCard number="03" title="Chat & Cite" desc="Ask questions. LangGraph retrieves chunks, and the agent answers with exact, clickable page citations." />
          </div>
        </motion.div>

      </main>
    </div>
  );
}

function FeatureCard({ icon: Icon, title, desc }: { icon: LucideIcon, title: string, desc: string }) {
  return (
    <motion.div variants={{ hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } }} 
      className="p-6 rounded-2xl bg-white/[0.03] border border-white/10 hover:bg-white/[0.05] transition-colors"
    >
      <div className="w-12 h-12 rounded-xl bg-indigo-500/20 flex items-center justify-center mb-6">
        <Icon className="w-6 h-6 text-indigo-400" />
      </div>
      <h3 className="text-lg font-semibold text-white mb-2">{title}</h3>
      <p className="text-slate-400 text-sm leading-relaxed">{desc}</p>
    </motion.div>
  );
}

function StepCard({ number, title, desc }: { number: string, title: string, desc: string }) {
  return (
    <motion.div variants={{ hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } }} className="relative p-8 rounded-2xl bg-gradient-to-b from-white/[0.05] to-transparent border border-white/[0.05]">
      <div className="text-5xl font-black text-white/[0.05] absolute top-6 right-6">{number}</div>
      <h3 className="text-xl font-bold text-white mb-4 relative z-10">{title}</h3>
      <p className="text-slate-400 text-sm leading-relaxed relative z-10">{desc}</p>
    </motion.div>
  );
}
