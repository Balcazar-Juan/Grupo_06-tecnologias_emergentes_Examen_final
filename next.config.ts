import type { NextConfig } from "next";

// El portal conserva la exportación estática; el Worker sirve los archivos
// y reenvía las solicitudes /api/* a FastAPI en Render.
const nextConfig: NextConfig = {
  output: "export",
  images: { unoptimized: true },
};

export default nextConfig;
