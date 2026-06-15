"use client";
import { useState, useEffect, useRef } from "react";
import { Mic } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface SpeechRecognitionAlternative {
  transcript: string;
}

interface SpeechRecognitionResult {
  0: SpeechRecognitionAlternative;
}

interface SpeechRecognitionEventLike {
  results: {
    length: number;
    [index: number]: SpeechRecognitionResult;
  };
}

interface SpeechRecognitionLike {
  continuous: boolean;
  interimResults: boolean;
  start: () => void;
  stop: () => void;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: (() => void) | null;
  onend: (() => void) | null;
}

interface WindowWithSpeechRecognition extends Window {
  webkitSpeechRecognition?: new () => SpeechRecognitionLike;
}

export function VoiceButton({ onTranscript }: { onTranscript: (t: string) => void }) {
  const [listening, setListening] = useState(false);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);

  useEffect(() => {
    const SpeechRecognition = (window as WindowWithSpeechRecognition).webkitSpeechRecognition;
    if (!SpeechRecognition) return;
    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;

    recognition.onresult = (e: SpeechRecognitionEventLike) => {
      let currentTranscript = "";
      for (let i = 0; i < e.results.length; ++i) {
        currentTranscript += e.results[i][0].transcript;
      }
      if (currentTranscript) onTranscript(currentTranscript);
    };

    recognition.onerror = () => setListening(false);
    recognition.onend = () => setListening(false);
    recognitionRef.current = recognition;
  }, [onTranscript]);

  const toggle = () => {
    if (listening) {
      recognitionRef.current?.stop();
      setListening(false);
    } else {
      recognitionRef.current?.start();
      setListening(true);
    }
  };

  return (
    <div className="relative flex items-center justify-center">
      <AnimatePresence>
        {listening && (
          <>
            <motion.div initial={{ scale: 0.8, opacity: 0 }} animate={{ scale: 2, opacity: 0 }} transition={{ repeat: Infinity, duration: 1.5, ease: "easeOut" }} className="absolute inset-0 bg-rose-500 rounded-full" />
            <motion.div initial={{ scale: 0.8, opacity: 0 }} animate={{ scale: 2, opacity: 0 }} transition={{ repeat: Infinity, duration: 1.5, delay: 0.5, ease: "easeOut" }} className="absolute inset-0 bg-rose-500 rounded-full" />
          </>
        )}
      </AnimatePresence>
      <button
        onClick={toggle}
        className={`relative z-10 p-3 rounded-2xl transition-colors ${
          listening ? "bg-rose-500 text-white" : "text-slate-400 hover:bg-white/5 hover:text-slate-200"
        }`}
        title="Voice Input"
      >
        <Mic className="w-5 h-5" />
      </button>
    </div>
  );
}
