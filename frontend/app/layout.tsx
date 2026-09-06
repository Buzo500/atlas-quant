import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = {
  title: 'ATLAS Quant · Cartera y laboratorio',
  description:
    'Análisis de cartera, experimentos reproducibles y evaluación de estrategias.',
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="es" className="dark">
      <body>{children}</body>
    </html>
  );
}
