"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useCamera } from "../hooks/useCamera";
import { useWakeLock } from "../hooks/useWakeLock";
import { useWebSocket } from "../hooks/useWebSocket";
import { EmotionBadge } from "./EmotionBadge";
import { ResultCard } from "./ResultCard";

export function LiveCamera() {
  const [sessionId] = useState(() => crypto.randomUUID());
  const [running, setRunning] = useState(false);
  const [emotion, setEmotion] = useState<string | null>(null);
  const [confidence, setConfidence] = useState<number | null>(null);
  const [interpretation, setInterpretation] = useState("");
  const [streaming, setStreaming] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const { videoRef, active, start: startCamera, stop: stopCamera, captureFrame } = useCamera();
  const wakeLock = useWakeLock();

  const onResult = useCallback((payload: Record<string, unknown>) => {
    const em = payload.overall_emotion as string | undefined;
    const conf = payload.confidence as number | undefined;
    if (em) setEmotion(em);
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
    mode: "video",
    onResult,
    onToken,
    onError,
  });

  const handleStart = async () => {
    await startCamera();
    ws.connect();
    await wakeLock.request();
    setRunning(true);
  };

  const handleStop = () => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    intervalRef.current = null;
    ws.disconnect();
    stopCamera();
    wakeLock.release();
    setRunning(false);
    setStreaming(false);
  };

  useEffect(() => {
    if (running && ws.connected && active) {
      intervalRef.current = setInterval(() => {
        const frame = captureFrame();
        if (frame) {
          ws.sendText(
            JSON.stringify({
              type: "frame",
              data: frame,
              timestamp: Date.now(),
            })
          );
        }
      }, 2500);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [running, ws.connected, active, captureFrame, ws]);

  useEffect(() => {
    if (streaming && interpretation) {
      const timer = setTimeout(() => setStreaming(false), 500);
      return () => clearTimeout(timer);
    }
  }, [interpretation, streaming]);

  return (
    <div className="flex flex-col h-full">
      <div className="relative flex-1 bg-black flex items-center justify-center">
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="w-full h-full object-cover"
        />
        {emotion && (
          <div className="absolute top-4 left-4">
            <EmotionBadge emotion={emotion} confidence={confidence} />
          </div>
        )}
        {!running && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/60">
            <p className="text-gray-400 text-lg">
              Toque no botão para iniciar
            </p>
          </div>
        )}
      </div>

      <ResultCard
        emotion={emotion}
        confidence={confidence}
        interpretation={interpretation}
        isStreaming={streaming}
      />

      <div className="flex justify-center pb-4">
        <button
          onClick={running ? handleStop : handleStart}
          className={`min-w-[64px] min-h-[64px] rounded-full text-white text-2xl font-bold shadow-lg transition-colors ${
            running
              ? "bg-red-600 active:bg-red-700"
              : "bg-[#e94560] active:bg-[#c73e54]"
          }`}
        >
          {running ? "■" : "▶"}
        </button>
      </div>
    </div>
  );
}
