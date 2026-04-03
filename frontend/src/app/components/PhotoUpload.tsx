"use client";

import { useCallback, useRef, useState } from "react";
import { uploadFile } from "../lib/api";
import { EmotionBadge, HypothesesBar } from "./EmotionBadge";
import { ResultCard } from "./ResultCard";

interface Hypothesis {
  state: string;
  probability: number;
}

interface AnalysisResult {
  vision?: Record<string, unknown>;
  interpretation?: string;
  provider?: string;
  frame_count?: number;
  aggregate?: Record<string, unknown>;
}

export function PhotoUpload() {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const [isVideo, setIsVideo] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [interpretation, setInterpretation] = useState("");
  const [error, setError] = useState<string | null>(null);

  const hypotheses = result?.vision?.hypotheses as Hypothesis[] | undefined;
  const uncertainty = result?.vision?.uncertainty as string | undefined;
  const conflict = result?.vision?.conflict as { detected: boolean; signals: string[] } | undefined;
  const latentState = result?.vision?.latent_state as { arousal: number; valence: number; perceived_safety: number } | undefined;

  const handleSelect = useCallback(() => {
    inputRef.current?.click();
  }, []);

  const handleFile = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const url = URL.createObjectURL(file);
    setPreview(url);
    setIsVideo(file.type.startsWith("video/"));
    setLoading(true);
    setError(null);
    setInterpretation("Analisando...");
    setResult(null);

    try {
      const res = await uploadFile(file);
      setResult(res);

      let text = res.interpretation || "Sem interpretação";
      if (res.frame_count) {
        text = `[${res.frame_count} frames analisados]\n\n${text}`;
      }
      setInterpretation(text);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Falha no upload";
      setError(msg);
      setInterpretation(`Erro: ${msg}`);
    } finally {
      setLoading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }, []);

  const handleClear = useCallback(() => {
    setPreview(null);
    setIsVideo(false);
    setResult(null);
    setInterpretation("");
    setError(null);
  }, []);

  return (
    <div className="flex flex-col items-center p-4">
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,video/mp4,video/quicktime"
        className="hidden"
        onChange={handleFile}
      />

      {/* Preview */}
      {preview ? (
        <div className="relative w-full max-w-md mb-4">
          {isVideo ? (
            <video
              src={preview}
              controls
              playsInline
              className="w-full rounded-2xl object-cover max-h-[50vh]"
            />
          ) : (
            <img
              src={preview}
              alt="Foto selecionada"
              className="w-full rounded-2xl object-cover max-h-[50vh]"
            />
          )}
          {hypotheses && hypotheses.length > 0 && (
            <div className="absolute top-4 left-4">
              <EmotionBadge hypotheses={hypotheses} uncertainty={uncertainty} />
            </div>
          )}
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center bg-black/50 rounded-2xl">
              <div className="w-10 h-10 border-4 border-[#e94560] border-t-transparent rounded-full animate-spin" />
            </div>
          )}
        </div>
      ) : (
        <div className="w-full max-w-md aspect-video bg-[#16213e] rounded-2xl flex flex-col items-center justify-center mb-4">
          <span className="text-5xl mb-4">📷</span>
          <p className="text-gray-400 text-center px-6">
            Selecione uma foto ou vídeo da galeria para análise
          </p>
        </div>
      )}

      {/* Result */}
      {(interpretation || error) && (
        <div className="w-full max-w-md">
          <ResultCard
            hypotheses={hypotheses}
            uncertainty={uncertainty}
            conflict={conflict}
            latentState={latentState}
            interpretation={interpretation}
            provider={result?.provider}
            aggregate={result?.aggregate as Record<string, unknown> | undefined}
          />
        </div>
      )}

      {/* Buttons */}
      <div className="flex gap-4 mt-2">
        {preview && (
          <button
            onClick={handleClear}
            className="min-w-[48px] min-h-[48px] px-6 rounded-full bg-gray-600 text-white text-sm font-semibold active:bg-gray-700"
          >
            Limpar
          </button>
        )}
        <button
          onClick={handleSelect}
          disabled={loading}
          className={`min-w-[48px] min-h-[48px] px-6 rounded-full text-white text-sm font-semibold ${
            loading
              ? "bg-gray-500"
              : "bg-[#e94560] active:bg-[#c73e54]"
          }`}
        >
          {loading ? "Analisando..." : preview ? "Outra foto" : "Escolher foto"}
        </button>
      </div>
    </div>
  );
}
