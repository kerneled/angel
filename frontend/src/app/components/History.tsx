"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchSessions } from "../lib/api";
import { EmotionBadge } from "./EmotionBadge";

interface SessionItem {
  id: string;
  mode: string;
  analysis_count: number;
  last_emotion: string | null;
  created_at: string | null;
  ended_at: string | null;
}

export function History() {
  const { data, isLoading, error } = useQuery<SessionItem[]>({
    queryKey: ["sessions"],
    queryFn: fetchSessions,
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

  return (
    <div className="p-4 space-y-3">
      <h2 className="text-lg font-semibold mb-2">Histórico</h2>
      {data.map((session) => (
        <div
          key={session.id}
          className="bg-[#16213e] rounded-xl p-4 flex items-center justify-between"
        >
          <div>
            <p className="text-sm text-gray-400">
              {session.created_at
                ? new Date(session.created_at).toLocaleString("pt-BR")
                : "—"}
            </p>
            <p className="text-sm text-gray-500">
              {session.mode} · {session.analysis_count} análises
            </p>
          </div>
          <EmotionBadge emotion={session.last_emotion} size="sm" />
        </div>
      ))}
    </div>
  );
}
