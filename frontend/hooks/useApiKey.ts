"use client";

import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "taxreform:api-key";

export function useApiKey() {
  const [apiKey, setApiKeyState] = useState<string>("");

  useEffect(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored) setApiKeyState(stored);
  }, []);

  const setApiKey = useCallback((value: string) => {
    window.localStorage.setItem(STORAGE_KEY, value);
    setApiKeyState(value);
  }, []);

  return { apiKey, setApiKey };
}
