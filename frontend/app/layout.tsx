import type { Metadata } from "next";
import { Fraunces, Source_Sans_3 } from "next/font/google";
import "./globals.css";

const display = Fraunces({
  subsets: ["latin"],
  variable: "--font-display",
});

const sans = Source_Sans_3({
  subsets: ["latin"],
  variable: "--font-sans",
});

export const metadata: Metadata = {
  title: "Prediction Content — Kelayakan IG/TikTok",
  description:
    "Prediksi apakah konten Instagram/TikTok layak tampil, lengkap dengan saran perbaikan.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="id">
      <body className={`${display.variable} ${sans.variable} antialiased`}>
        {children}
      </body>
    </html>
  );
}
