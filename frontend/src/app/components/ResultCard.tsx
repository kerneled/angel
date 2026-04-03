"use client";

import { EmotionBadge } from "./EmotionBadge";

interface ResultCardProps {
  emotion?: string | null;
  confidence?: number | null;
  interpretation: string;
  isStreaming?: boolean;
}

export function ResultCard({
  emotion,
  confidence,
  interpretation,
  isStreaming = false,
}: ResultCardProps) {
  return (
    <div className="bg-[#16213e] rounded-2xl p-4 mx-4 mb-4 shadow-lg">
      <div className="flex items-center justify-between mb-3">
        <EmotionBadge emotion={emotion} confidence={confidence} />
        {isStreaming && (
          <span className="w-2 h-2 rounded-full bg-[#e94560] animate-pulse" />
        )}
      </div>
      <p className="text-base leading-relaxed text-gray-200 min-h-[48px]">
        {interpretation || (
          <span className="text-gray-500">Aguardando análise...</span>
        )}
      </p>
    </div>
  );
}
