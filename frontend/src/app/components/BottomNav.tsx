"use client";

type Tab = "audio" | "camera" | "history";

interface BottomNavProps {
  active: Tab;
  onTabChange: (tab: Tab) => void;
}

const tabs: { id: Tab; label: string; icon: string }[] = [
  { id: "audio", label: "Audio", icon: "🔊" },
  { id: "camera", label: "Câmera", icon: "🎥" },
  { id: "history", label: "Histórico", icon: "📋" },
];

export function BottomNav({ active, onTabChange }: BottomNavProps) {
  return (
    <nav className="flex items-center justify-around bg-[#16213e] border-t border-gray-700 pb-[env(safe-area-inset-bottom)]">
      {tabs.map((t) => (
        <button
          key={t.id}
          onClick={() => onTabChange(t.id)}
          className={`flex flex-col items-center justify-center min-w-[48px] min-h-[48px] py-2 px-4 transition-colors ${
            active === t.id
              ? "text-[#e94560]"
              : "text-gray-400 active:text-gray-200"
          }`}
        >
          <span className="text-2xl">{t.icon}</span>
          <span className="text-xs mt-1">{t.label}</span>
        </button>
      ))}
    </nav>
  );
}
