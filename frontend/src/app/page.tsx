"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import type { Tab } from "./components/BottomNav";

const BottomNav = dynamic(() => import("./components/BottomNav").then(m => ({ default: m.BottomNav })), { ssr: false });
const LiveCamera = dynamic(() => import("./components/LiveCamera").then(m => ({ default: m.LiveCamera })), { ssr: false });
const LiveAudio = dynamic(() => import("./components/LiveAudio").then(m => ({ default: m.LiveAudio })), { ssr: false });
const PhotoUpload = dynamic(() => import("./components/PhotoUpload").then(m => ({ default: m.PhotoUpload })), { ssr: false });
const History = dynamic(() => import("./components/History").then(m => ({ default: m.History })), { ssr: false });

export default function Home() {
  const [tab, setTab] = useState<Tab>("camera");

  return (
    <div className="flex flex-col h-dvh">
      <header className="flex items-center justify-center py-3 px-4 bg-[#16213e]">
        <h1 className="text-lg font-bold tracking-wide">DogSense</h1>
      </header>

      <main className="flex-1 overflow-y-auto">
        {tab === "camera" && <LiveCamera />}
        {tab === "upload" && <PhotoUpload />}
        {tab === "audio" && <LiveAudio />}
        {tab === "history" && <History />}
      </main>

      <BottomNav active={tab} onTabChange={setTab} />
    </div>
  );
}
