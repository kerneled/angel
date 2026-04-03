"use client";

import Markdown from "react-markdown";
import { EmotionBadge, HypothesesBar } from "./EmotionBadge";

interface Hypothesis {
  state: string;
  probability: number;
}

interface ResultCardProps {
  hypotheses?: Hypothesis[] | null;
  uncertainty?: string | null;
  conflict?: { detected: boolean; signals: string[] } | null;
  latentState?: { arousal: number; valence: number; perceived_safety: number } | null;
  interpretation: string;
  isStreaming?: boolean;
  costUsd?: number | null;
  provider?: string | null;
  latencyMs?: number | null;
  aggregate?: {
    frame_count?: number;
    dominant_state?: string;
    state_stability?: number;
    avg_arousal?: number;
    avg_valence?: number;
    avg_safety?: number;
    trend?: string;
    conflict_count?: number;
  } | null;
  // Legacy
  state?: string | null;
  confidence?: number | null;
  urgency?: string | null;
}

const TREND_LABELS: Record<string, string> = {
  improving: "↗ Melhorando",
  stable: "→ Estável",
  deteriorating: "↘ Piorando",
};

export function ResultCard({
  hypotheses,
  uncertainty,
  conflict,
  latentState,
  interpretation,
  isStreaming = false,
  costUsd,
  provider,
  latencyMs,
  aggregate,
  state,
  confidence,
}: ResultCardProps) {
  return (
    <div className="bg-[#16213e] rounded-2xl p-4 mx-4 mb-4 shadow-lg">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <EmotionBadge
          hypotheses={hypotheses}
          uncertainty={uncertainty}
          state={state}
          confidence={confidence}
        />
        {isStreaming && (
          <span className="w-2 h-2 rounded-full bg-[#e94560] animate-pulse" />
        )}
      </div>

      {/* Hypotheses bars */}
      {hypotheses && hypotheses.length > 1 && (
        <HypothesesBar hypotheses={hypotheses} />
      )}

      {/* Conflict warning */}
      {conflict?.detected && conflict.signals.length > 0 && (
        <div className="mt-2 p-2 bg-yellow-900/30 rounded-lg text-xs text-yellow-300">
          ⚠ Sinais conflitantes: {conflict.signals.join(", ")}
        </div>
      )}

      {/* Latent state indicators */}
      {latentState && (
        <div className="mt-2 flex gap-3 text-xs text-gray-400">
          <span>Arousal: {latentState.arousal}/10</span>
          <span>Valência: {latentState.valence > 0 ? "+" : ""}{latentState.valence.toFixed(1)}</span>
          <span>Segurança: {latentState.perceived_safety}/10</span>
        </div>
      )}

      {/* Interpretation narrative (markdown) */}
      <div className="mt-3 text-base leading-relaxed text-gray-200 min-h-[48px] prose prose-invert prose-sm max-w-none">
        {interpretation ? (
          <Markdown>{interpretation}</Markdown>
        ) : (
          <p className="text-gray-500">Aguardando análise...</p>
        )}
      </div>

      {/* Aggregate bar */}
      {aggregate && aggregate.frame_count && aggregate.frame_count > 1 && (
        <div className="mt-3 pt-3 border-t border-gray-700 flex flex-wrap gap-3 text-xs text-gray-400">
          <span>{aggregate.frame_count} frames</span>
          {aggregate.trend && (
            <span>{TREND_LABELS[aggregate.trend] || aggregate.trend}</span>
          )}
          {aggregate.avg_arousal != null && (
            <span>Arousal: {aggregate.avg_arousal}</span>
          )}
          {aggregate.state_stability != null && (
            <span>Estab: {Math.round(aggregate.state_stability * 100)}%</span>
          )}
          {aggregate.conflict_count != null && aggregate.conflict_count > 0 && (
            <span>⚠ {aggregate.conflict_count} conflitos</span>
          )}
        </div>
      )}

      {/* Footer: cost + provider + latency */}
      {(costUsd != null || provider || latencyMs != null) && (
        <div className="mt-2 pt-2 border-t border-gray-700 flex items-center gap-3 text-xs text-gray-500">
          {provider && <span>{provider}</span>}
          {latencyMs != null && <span>{(latencyMs / 1000).toFixed(1)}s</span>}
          {uncertainty && <span>Incerteza: {uncertainty}</span>}
          {costUsd != null && (
            <span className="ml-auto">
              ${costUsd < 0.01 ? costUsd.toFixed(5) : costUsd.toFixed(3)}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
