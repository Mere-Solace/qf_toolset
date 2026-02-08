import { useEffect, useRef, useState, useCallback } from "react";
import wsManager from "@/api/ws";
import type { PriceUpdate } from "@/types";

export function useWebSocket(tickers?: string[]) {
  const [prices, setPrices] = useState<Record<string, PriceUpdate>>({});
  const tickerSet = useRef(new Set(tickers ?? []));

  useEffect(() => {
    tickerSet.current = new Set(tickers ?? []);
  }, [tickers]);

  const handleUpdate = useCallback((update: PriceUpdate) => {
    if (tickerSet.current.size === 0 || tickerSet.current.has(update.ticker)) {
      setPrices((prev) => ({ ...prev, [update.ticker]: update }));
    }
  }, []);

  useEffect(() => {
    const unsubscribe = wsManager.subscribe(handleUpdate);
    return unsubscribe;
  }, [handleUpdate]);

  return prices;
}
