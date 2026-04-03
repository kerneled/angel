"use client";

import { useCallback, useRef } from "react";

export function useWakeLock() {
  const lockRef = useRef<WakeLockSentinel | null>(null);

  const request = useCallback(async () => {
    try {
      if ("wakeLock" in navigator) {
        lockRef.current = await navigator.wakeLock.request("screen");
      }
    } catch {
      // WakeLock not supported or denied
    }
  }, []);

  const release = useCallback(async () => {
    try {
      await lockRef.current?.release();
      lockRef.current = null;
    } catch {
      // already released
    }
  }, []);

  return { request, release };
}
