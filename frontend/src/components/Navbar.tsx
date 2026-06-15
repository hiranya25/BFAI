"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import { useState } from "react";
import { FileText, MessageSquare, Home, Sparkles, Database } from "lucide-react";
import { DatabaseSidebar } from "./DatabaseSidebar";

export function Navbar() {
  const pathname = usePathname();

  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const navItems = [
    { name: "Home", path: "/", icon: Home },
    { name: "Upload", path: "/upload", icon: FileText },
    { name: "Agent Chat", path: "/chat", icon: MessageSquare },
  ];

  return (
    <>
      <nav className="fixed top-0 w-full z-50 border-b border-white/5 bg-[#0B0F19]/60 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2 group">
          <div className="p-2 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <span className="font-bold text-lg tracking-tight text-white group-hover:text-indigo-400 transition-colors">
            Agentic<span className="text-white/50">RAG</span>
          </span>
        </Link>

        <div className="flex items-center gap-1">
          {navItems.map((item) => {
            const isActive = pathname === item.path;
            const Icon = item.icon;
            return (
              <Link
                key={item.path}
                href={item.path}
                className={`relative px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isActive ? "text-white" : "text-white/60 hover:text-white hover:bg-white/5"
                }`}
              >
                {isActive && (
                  <motion.div
                    layoutId="nav-pill"
                    className="absolute inset-0 bg-white/10 rounded-lg"
                    transition={{ type: "spring", stiffness: 300, damping: 30 }}
                  />
                )}
                <span className="relative flex items-center gap-2">
                  <Icon className="w-4 h-4" />
                  {item.name}
                </span>
              </Link>
            );
          })}
          
          <div className="w-px h-6 bg-white/10 mx-2" />
          
          <button
            onClick={() => setIsSidebarOpen(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-indigo-400 bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/20 transition-colors"
          >
            <Database className="w-4 h-4" />
            Database
          </button>
        </div>
      </div>
    </nav>

    <DatabaseSidebar isOpen={isSidebarOpen} onClose={() => setIsSidebarOpen(false)} />
  </>
  );
}
