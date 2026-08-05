export function isEmailAllowed(
  email: string | null | undefined,
  allowlistEnv: string | undefined,
): boolean {
  if (!email || !allowlistEnv) return false;
  const allowed = allowlistEnv
    .split(",")
    .map((entry) => entry.trim().toLowerCase())
    .filter(Boolean);
  return allowed.includes(email.toLowerCase());
}
