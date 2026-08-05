import { describe, expect, it } from "vitest";

import { isEmailAllowed } from "./auth-allowlist";

describe("isEmailAllowed", () => {
  it("permite um e-mail presente na allowlist", () => {
    expect(isEmailAllowed("dev@example.com", "dev@example.com,ops@example.com")).toBe(true);
  });

  it("recusa um e-mail ausente da allowlist", () => {
    expect(isEmailAllowed("intruso@example.com", "dev@example.com")).toBe(false);
  });

  it("ignora diferenças de maiúsculas/minúsculas", () => {
    expect(isEmailAllowed("Dev@Example.com", "dev@example.com")).toBe(true);
  });

  it("ignora espaços ao redor de cada entrada da allowlist", () => {
    expect(isEmailAllowed("dev@example.com", " dev@example.com , ops@example.com ")).toBe(true);
  });

  it("recusa quando o e-mail está ausente", () => {
    expect(isEmailAllowed(null, "dev@example.com")).toBe(false);
    expect(isEmailAllowed(undefined, "dev@example.com")).toBe(false);
  });

  it("recusa quando a allowlist não está configurada", () => {
    expect(isEmailAllowed("dev@example.com", undefined)).toBe(false);
    expect(isEmailAllowed("dev@example.com", "")).toBe(false);
  });
});
