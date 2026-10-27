import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "HyperMat IA | Matrícula universitaria",
  description: "Plataforma de hiperautomatización del proceso de matrícula universitaria.",
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body className="antialiased">{children}</body>
    </html>
  );
}
