"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchSessions, fetchSessionDetail } from "../lib/api";
import { EmotionBadge } from "./EmotionBadge";

interface SessionItem {
  id: string;
  mode: string;
  analysis_count: number;
  last_state: string | null;
  last_interpretation: string | null;
  last_provider: string | null;
  created_at: string | null;
  ended_at: string | null;
}

interface AnalysisItem {
  id: string;
  mode: string;
  vision: Record<string, unknown> | null;
  audio: Record<string, unknown> | null;
  interpretation: string | null;
  provider: string | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  latency_ms: number | null;
  created_at: string | null;
}

export function History() {
  const [selectedSession, setSelectedSession] = useState<string | null>(null);

  const { data, isLoading, error } = useQuery<SessionItem[]>({
    queryKey: ["sessions"],
    queryFn: fetchSessions,
  });

  const { data: analyses } = useQuery<AnalysisItem[]>({
    queryKey: ["session-detail", selectedSession],
    queryFn: () => fetchSessionDetail(selectedSession!),
    enabled: !!selectedSession,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-gray-400">Carregando...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-red-400">Erro ao carregar histórico</p>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-gray-500">Nenhuma sessão registrada</p>
      </div>
    );
  }

  // Detail view
  if (selectedSession && analyses) {
    return (
      <div className="p-4">
        <button
          onClick={() => setSelectedSession(null)}
          className="text-[#e94560] text-sm mb-4 min-h-[48px] flex items-center"
        >
          ← Voltar ao histórico
        </button>

        <h2 className="text-lg font-semibold mb-3">
          Sessão {selectedSession.slice(0, 8)}...
        </h2>

        {analyses.length === 0 && (
          <p className="text-gray-500">Nenhuma análise nesta sessão</p>
        )}

        <div className="space-y-4">
          {analyses.map((a, i) => (
            <div key={a.id} className="bg-[#16213e] rounded-xl p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-gray-500">
                  #{i + 1} ·{" "}
                  {a.created_at
                    ? new Date(a.created_at).toLocaleTimeString("pt-BR")
                    : "—"}
                </span>
                <div className="flex items-center gap-2 text-xs text-gray-500">
                  {a.provider && <span>{a.provider}</span>}
                  {a.latency_ms != null && (
                    <span>{(a.latency_ms / 1000).toFixed(1)}s</span>
                  )}
                  {a.prompt_tokens != null && a.completion_tokens != null && (
                    <span>
                      {a.prompt_tokens}+{a.completion_tokens} tok
                    </span>
                  )}
                </div>
              </div>

              {a.vision && (
                <div className="mb-2">
                  <EmotionBadge
                    state={
                      (a.vision.behavioral_state as string) ??
                      (a.vision.overall_emotion as string)
                    }
                    confidence={a.vision.confidence as number}
                    urgency={a.vision.urgency as string}
                    size="sm"
                  />
                  {a.vision.breed_guess && (
                    <span className="ml-2 text-xs text-gray-400">
                      {a.vision.breed_guess as string}
                    </span>
                  )}
                  {a.vision.sleep_position &&
                    a.vision.sleep_position !== "not-sleeping" && (
                      <span className="ml-2 text-xs text-gray-400">
                        Posição: {a.vision.sleep_position as string}
                      </span>
                    )}
                </div>
              )}

              {a.interpretation && (
                <p className="text-sm text-gray-300 leading-relaxed">
                  {a.interpretation}
                </p>
              )}
            </div>
          ))}
        </div>
      </div>
    );
  }

  // List view
  return (
    <div className="p-4 space-y-3">
      <h2 className="text-lg font-semibold mb-2">Histórico</h2>
      {data.map((session) => (
        <button
          key={session.id}
          onClick={() =>
            session.analysis_count > 0 && setSelectedSession(session.id)
          }
          className="w-full bg-[#16213e] rounded-xl p-4 text-left"
        >
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-gray-400">
              {session.created_at
                ? new Date(session.created_at).toLocaleString("pt-BR")
                : "—"}
            </p>
            <EmotionBadge state={session.last_state} size="sm" />
          </div>
          <p className="text-xs text-gray-500 mb-1">
            {session.mode} · {session.analysis_count} análises
            {session.last_provider && ` · ${session.last_provider}`}
          </p>
          {session.last_interpretation && (
            <p className="text-sm text-gray-400 line-clamp-2">
              {session.last_interpretation}
            </p>
          )}
        </button>
      ))}
    </div>
  );
}
