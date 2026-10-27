import type { NextConfig } from "next";

// Despliegue del portal en Cloudflare Pages: sin SSR ni backend Next.js.
// Las solicitudes de negocio se realizan desde el navegador a FastAPI en Render.
const nextConfig: NextConfig = {
  output: "export",
  images: { unoptimized: true },
};

export default nextConfig;
