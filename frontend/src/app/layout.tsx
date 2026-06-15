import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Navbar } from "@/components/Navbar";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Document Intelligence | Agentic RAG",
  description: "Upload and chat with your documents using Gemini 1.5 Flash.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.className} h-full antialiased dark`}>
      <body className="min-h-full flex flex-col bg-[#0B0F19] text-slate-300 selection:bg-indigo-500/30">
        <Navbar />
        {children}
      </body>
    </html>
  );
}
