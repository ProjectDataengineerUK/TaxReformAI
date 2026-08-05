import NextAuth from "next-auth";
import Google from "next-auth/providers/google";

import { isEmailAllowed } from "./auth-allowlist";

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [Google],
  session: { strategy: "jwt" },
  pages: { signIn: "/login" },
  callbacks: {
    async signIn({ user }) {
      return isEmailAllowed(user.email, process.env.ALLOWED_EMAILS);
    },
  },
});
