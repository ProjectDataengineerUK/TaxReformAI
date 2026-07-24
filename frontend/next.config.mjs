/** @type {import('next').NextConfig} */
const nextConfig = {
  // Necessário para o build multi-stage do Dockerfile (Cloud Run) — gera
  // .next/standalone com um server.js mínimo, sem precisar de `npm install`
  // em produção nem copiar node_modules inteiro pra imagem final.
  output: "standalone",
};

export default nextConfig;
