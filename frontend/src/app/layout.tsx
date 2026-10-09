import type { Metadata, Viewport } from "next";
import "./globals.css";
import { Toaster } from "sonner";

export const metadata: Metadata = {
  title: "AI Tutor",
  description: "Personalized AI tutor for school students",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  viewportFit: "cover",
  themeColor: "#4f46e5",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="h-full">
        {children}
        <Toaster position="top-center" />
      </body>
    </html>
  );
}
