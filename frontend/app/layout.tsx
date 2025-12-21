import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { ToastProvider } from "@/components/ui/use-toast";
import "./globals.css";
import { Navbar } from "@/components/layout/navbar";
import { createClient } from "@/lib/supabase/server";
import NextTopLoader from 'nextjs-toploader';

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Kiwin - AI Agent Platform",
  description: "Build, train, and deploy AI agents in minutes.",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <NextTopLoader
          color="hsl(var(--primary))"
          height={3}
          showSpinner={false}
          shadow="0 0 10px hsl(var(--primary)),0 0 5px hsl(var(--primary))"
        />
        <ToastProvider>
          <Navbar user={user} />
          <main className="min-h-[calc(100vh-3.5rem)]">
            {children}
          </main>
        </ToastProvider>


      </body>
    </html>
  );
}
