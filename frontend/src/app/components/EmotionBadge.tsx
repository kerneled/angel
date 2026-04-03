"use client";

const STATE_COLORS: Record<string, string> = {
  relaxed: "bg-green-500",
  playful: "bg-emerald-400",
  excited: "bg-amber-400",
  anxious: "bg-orange-400",
  fearful: "bg-orange-600",
  defensive_aggression: "bg-red-700",
  offensive_aggression: "bg-red-800",
};

const STATE_LABELS: Record<string, string> = {
  relaxed: "Relaxado",
  playful: "Brincalhão",
  excited: "Excitado",
  anxious: "Ansioso",
  fearful: "Com medo",
  defensive_aggression: "Agressão defensiva",
  offensive_aggression: "Agressão ofensiva",
};

const UNCERTAINTY_INDICATOR: Record<string, string> = {
  low: "●",
  medium: "◐",
  high: "○",
};

interface Hypothesis {
  state: string;
  probability: number;
}

interface EmotionBadgeProps {
  hypotheses?: Hypothesis[] | null;
  uncertainty?: string | null;
  // Legacy support
  state?: string | null;
  confidence?: number | null;
  size?: "sm" | "lg";
}

export function EmotionBadge({
  hypotheses,
  uncertainty,
  state: legacyState,
  confidence: legacyConfidence,
  size = "lg",
}: EmotionBadgeProps) {
  // Determine primary state
  let primary: string | null = null;
  let probability: number | null = null;

  if (hypotheses && hypotheses.length > 0) {
    const best = hypotheses.reduce((a, b) =>
      a.probability > b.probability ? a : b
    );
    primary = best.state;
    probability = best.probability;
  } else if (legacyState) {
    primary = legacyState;
    probability = legacyConfidence;
  }

  if (!primary) return null;

  const color = STATE_COLORS[primary] || "bg-gray-600";
  const label = STATE_LABELS[primary] || primary;
  const uncIcon = uncertainty ? UNCERTAINTY_INDICATOR[uncertainty] || "" : "";
  const sizeClass =
    size === "lg" ? "text-base px-4 py-2" : "text-sm px-3 py-1";

  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full font-semibold text-white ${color} ${sizeClass}`}
    >
      {uncIcon && <span className="opacity-75">{uncIcon}</span>}
      {label}
      {probability != null && (
        <span className="opacity-75 text-sm">
          {Math.round(probability * 100)}%
        </span>
      )}
    </span>
  );
}

/**
 * Displays all hypotheses as small bars.
 */
export function HypothesesBar({
  hypotheses,
}: {
  hypotheses: Hypothesis[];
}) {
  if (!hypotheses || hypotheses.length === 0) return null;

  const sorted = [...hypotheses].sort((a, b) => b.probability - a.probability);

  return (
    <div className="flex flex-col gap-1 mt-2">
      {sorted.map((h) => (
        <div key={h.state} className="flex items-center gap-2 text-xs">
          <span className="w-28 text-gray-400 truncate">
            {STATE_LABELS[h.state] || h.state}
          </span>
          <div className="flex-1 h-2 bg-gray-700 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full ${STATE_COLORS[h.state] || "bg-gray-500"}`}
              style={{ width: `${h.probability * 100}%` }}
            />
          </div>
          <span className="w-10 text-right text-gray-500">
            {Math.round(h.probability * 100)}%
          </span>
        </div>
      ))}
    </div>
  );
}
