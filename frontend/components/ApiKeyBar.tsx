"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useApiKey } from "@/hooks/useApiKey";

export function ApiKeyBar() {
  const { apiKey, setApiKey } = useApiKey();
  const [draft, setDraft] = useState(apiKey);

  useEffect(() => {
    setDraft(apiKey);
  }, [apiKey]);

  return (
    <div className="flex items-center gap-2 border-b border-border bg-surface px-4 py-2">
      <label htmlFor="api-key-input" className="text-xs font-medium text-muted-foreground">
        API Key
      </label>
      <Input
        id="api-key-input"
        type="password"
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        placeholder="Cole sua API key"
        className="h-8 max-w-xs text-xs"
      />
      <Button size="sm" variant="outline" onClick={() => setApiKey(draft)}>
        Salvar
      </Button>
      {apiKey && <span className="text-xs text-accent">Configurada</span>}
    </div>
  );
}
