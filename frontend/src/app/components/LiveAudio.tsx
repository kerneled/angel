"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useWakeLock } from "../hooks/useWakeLock";
import { useWebSocket } from "../hooks/useWebSocket";
import { EmotionBadge } from "./EmotionBadge";
import { ResultCard } from "./ResultCard";

export function LiveAudio() {
  const [sessionId] = useState(() => crypto.randomUUID?.() ?? Math.random().toString(36).slice(2) + Date.now().toString(36));
  const [running, setRunning] = useState(false);
  const [emotion, setEmotion] = useState<string | null>(null);
  const [confidence, setConfidence] = useState<number | null>(null);
  const [interpretation, setInterpretation] = useState("");
  const [streaming, setStreaming] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const wakeLock = useWakeLock();

  const onResult = useCallback((payload: Record<string, unknown>) => {
    const label = payload.label as string | undefined;
    const conf = payload.confidence as number | undefined;
    if (label) setEmotion(label);
    if (conf != null) setConfidence(conf);
    setInterpretation("");
    setStreaming(true);
  }, []);

  const onToken = useCallback((token: string) => {
    setInterpretation((prev) => prev + token);
  }, []);

  const onError = useCallback((msg: string) => {
    setInterpretation(`Erro: ${msg}`);
    setStreaming(false);
  }, []);

  const ws = useWebSocket({
    sessionId,
    mode: "audio",
    onResult,
    onToken,
    onError,
  });

  const handleStart = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    streamRef.current = stream;

    const recorder = new MediaRecorder(stream);
    mediaRecorderRef.current = recorder;

    recorder.ondataavailable = async (e) => {
      if (e.data.size > 0) {
        const buffer = await e.data.arrayBuffer();
        ws.sendBinary(buffer);
      }
    };

    ws.connect();
    await wakeLock.request();
    recorder.start(3000);
    setRunning(true);
  };

  const handleStop = () => {
    mediaRecorderRef.current?.stop();
    streamRef.current?.getTracks().forEach((t) => t.stop());
    mediaRecorderRef.current = null;
    streamRef.current = null;
    ws.disconnect();
    wakeLock.release();
    setRunning(false);
    setStreaming(false);
  };

  useEffect(() => {
    if (streaming && interpretation) {
      const timer = setTimeout(() => setStreaming(false), 500);
      return () => clearTimeout(timer);
    }
  }, [interpretation, streaming]);

  return (
    <div className="flex flex-col h-full items-center">
      <div className="flex-1 flex flex-col items-center justify-center px-4">
        <div
          className={`w-32 h-32 rounded-full flex items-center justify-center mb-6 transition-colors ${
            running ? "bg-[#e94560]/20 animate-pulse" : "bg-[#16213e]"
          }`}
        >
          <span className="text-5xl">🎤</span>
        </div>

        {emotion && (
          <div className="mb-4">
            <EmotionBadge emotion={emotion} confidence={confidence} />
          </div>
        )}

        <p className="text-gray-400 text-center mb-6">
          {running
            ? "Ouvindo... aponte o microfone para o cachorro"
            : "Toque no botão para gravar áudio"}
        </p>
      </div>

      <ResultCard
        emotion={emotion}
        confidence={confidence}
        interpretation={interpretation}
        isStreaming={streaming}
      />

      {/* FAB - floating action button */}
      <button
        onClick={running ? handleStop : handleStart}
        className={`fixed bottom-24 right-6 z-50 w-16 h-16 rounded-full text-white text-2xl font-bold shadow-xl transition-colors ${
          running
            ? "bg-red-600 active:bg-red-700"
            : "bg-[#e94560] active:bg-[#c73e54]"
        }`}
      >
        {running ? "■" : "▶"}
      </button>
    </div>
  );
}
