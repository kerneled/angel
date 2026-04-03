"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useCamera } from "../hooks/useCamera";
import { useWakeLock } from "../hooks/useWakeLock";
import { useWebSocket } from "../hooks/useWebSocket";
import { EmotionBadge } from "./EmotionBadge";
import { ResultCard } from "./ResultCard";

interface Hypothesis {
  state: string;
  probability: number;
}

interface AnalysisPayload {
  hypotheses?: Hypothesis[];
  uncertainty?: string;
  conflict?: { detected: boolean; signals: string[] };
  latent_state?: { arousal: number; valence: number; perceived_safety: number };
  aggregate?: Record<string, unknown>;
  cost_usd?: number;
  provider?: string;
  latency_ms?: number;
}

export function LiveCamera() {
  const [sessionId] = useState(
    () =>
      crypto.randomUUID?.() ??
      Math.random().toString(36).slice(2) + Date.now().toString(36)
  );
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<AnalysisPayload | null>(null);
  const [interpretation, setInterpretation] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [status, setStatus] = useState("Toque no botão para iniciar");
  const [error, setError] = useState<string | null>(null);
  const [sessionCost, setSessionCost] = useState(0);
  const [framesSent, setFramesSent] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const {
    videoRef,
    active,
    start: startCamera,
    stop: stopCamera,
    captureFrame,
  } = useCamera();
  const wakeLock = useWakeLock();
  const captureFrameRef = useRef(captureFrame);
  captureFrameRef.current = captureFrame;

  const onResult = useCallback((payload: Record<string, unknown>) => {
    setResult(payload as unknown as AnalysisPayload);
    if (payload.cost_usd != null) {
      setSessionCost((prev) => prev + (payload.cost_usd as number));
    }
    setInterpretation("");
    setStreaming(true);
    setStatus("Análise recebida");
  }, []);

  const onToken = useCallback((token: string) => {
    setInterpretation((prev) => prev + token);
  }, []);

  const onError = useCallback((msg: string) => {
    setInterpretation(`Erro: ${msg}`);
    setStatus(`Erro: ${msg}`);
    setStreaming(false);
  }, []);

  const startCapturing = useCallback(() => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    console.log("[DogSense] Starting frame capture");
    setStatus("Enviando frames...");
    intervalRef.current = setInterval(() => {
      const frame = captureFrameRef.current();
      if (frame) {
        sendTextRef.current(
          JSON.stringify({ type: "frame", data: frame, timestamp: Date.now() })
        );
        setFramesSent((n) => n + 1);
      }
    }, 2500);
  }, []);

  const stopCapturing = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const ws = useWebSocket({
    sessionId,
    mode: "video",
    onResult,
    onToken,
    onError,
    onConnected: startCapturing,
  });

  const sendTextRef = useRef(ws.sendText);
  sendTextRef.current = ws.sendText;

  useEffect(() => {
    if (running && ws.connected && active && !intervalRef.current) {
      startCapturing();
    }
  }, [running, ws.connected, active, startCapturing]);

  useEffect(() => {
    return () => stopCapturing();
  }, [stopCapturing]);

  const handleStart = async () => {
    setError(null);
    setSessionCost(0);
    setFramesSent(0);
    setResult(null);
    setStatus("Iniciando câmera...");
    try {
      await startCamera();
      setStatus("Câmera OK. Conectando...");
    } catch (e) {
      const msg = e instanceof Error ? e.message : "permissão negada";
      setError(`Câmera: ${msg}`);
      setStatus(`Erro: ${msg}`);
      return;
    }
    ws.connect();
    setStatus("Aguardando conexão WebSocket...");
    await wakeLock.request();
    setRunning(true);
  };

  const handleStop = () => {
    stopCapturing();
    ws.disconnect();
    stopCamera();
    wakeLock.release();
    setRunning(false);
    setStreaming(false);
    setStatus("Toque no botão para iniciar");
  };

  useEffect(() => {
    if (streaming && interpretation) {
      const timer = setTimeout(() => setStreaming(false), 500);
      return () => clearTimeout(timer);
    }
  }, [interpretation, streaming]);

  return (
    <div
      className="relative flex flex-col"
      style={{ minHeight: "calc(100dvh - 100px)" }}
    >
      <div className="relative aspect-video bg-black flex items-center justify-center">
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="w-full h-full object-cover"
        />
        {result?.hypotheses && running && (
          <div className="absolute top-4 left-4">
            <EmotionBadge
              hypotheses={result.hypotheses}
              uncertainty={result.uncertainty}
            />
          </div>
        )}
        {!running && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/60">
            <p className="text-gray-400 text-lg text-center px-8">
              {error ?? "Toque no botão para iniciar"}
            </p>
          </div>
        )}
      </div>

      {/* Status line */}
      <div className="px-4 py-2 flex items-center justify-between text-xs text-gray-500">
        <span>
          {status} {ws.connected ? "● WS" : "○ WS"}
          {framesSent > 0 && ` · ${framesSent} frames`}
        </span>
        {sessionCost > 0 && <span>Sessão: ${sessionCost.toFixed(4)}</span>}
      </div>

      <ResultCard
        hypotheses={result?.hypotheses}
        uncertainty={result?.uncertainty}
        conflict={result?.conflict as { detected: boolean; signals: string[] } | undefined}
        latentState={result?.latent_state as { arousal: number; valence: number; perceived_safety: number } | undefined}
        interpretation={interpretation}
        isStreaming={streaming}
        costUsd={result?.cost_usd}
        provider={result?.provider}
        latencyMs={result?.latency_ms}
        aggregate={result?.aggregate as Record<string, unknown> | undefined}
      />

      {/* FAB */}
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
