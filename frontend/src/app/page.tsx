"use client";

import { useState } from "react";
import { BottomNav } from "./components/BottomNav";
import { LiveAudio } from "./components/LiveAudio";
import { LiveCamera } from "./components/LiveCamera";
import { History } from "./components/History";

type Tab = "audio" | "camera" | "history";

export default function Home() {
  const [tab, setTab] = useState<Tab>("camera");

  return (
    <div className="flex flex-col h-dvh">
      <header className="flex items-center justify-center py-3 px-4 bg-[#16213e]">
        <h1 className="text-lg font-bold tracking-wide">DogSense</h1>
      </header>

      <main className="flex-1 overflow-y-auto">
        {tab === "audio" && <LiveAudio />}
        {tab === "camera" && <LiveCamera />}
        {tab === "history" && <History />}
      </main>

      <BottomNav active={tab} onTabChange={setTab} />
    </div>
  );
}
