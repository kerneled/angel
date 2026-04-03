"use client";

const EMOTION_COLORS: Record<string, string> = {
  happy: "bg-green-500",
  playful: "bg-emerald-400",
  neutral: "bg-gray-500",
  anxious: "bg-yellow-500",
  fearful: "bg-orange-500",
  aggressive: "bg-red-600",
  pain: "bg-red-800",
};

const EMOTION_LABELS: Record<string, string> = {
  happy: "Feliz",
  playful: "Brincalhão",
  neutral: "Neutro",
  anxious: "Ansioso",
  fearful: "Com medo",
  aggressive: "Agressivo",
  pain: "Com dor",
  alert: "Alerta",
  fear: "Medo",
  loneliness: "Solidão",
  attention: "Atenção",
  aggression: "Agressão",
};

interface EmotionBadgeProps {
  emotion: string | null | undefined;
  confidence?: number | null;
  size?: "sm" | "lg";
}

export function EmotionBadge({
  emotion,
  confidence,
  size = "lg",
}: EmotionBadgeProps) {
  if (!emotion) return null;

  const color = EMOTION_COLORS[emotion] || "bg-gray-600";
  const label = EMOTION_LABELS[emotion] || emotion;
  const sizeClass =
    size === "lg" ? "text-base px-4 py-2" : "text-sm px-3 py-1";

  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full font-semibold text-white ${color} ${sizeClass}`}
    >
      {label}
      {confidence != null && (
        <span className="opacity-75 text-sm">
          {Math.round(confidence * 100)}%
        </span>
      )}
    </span>
  );
}
