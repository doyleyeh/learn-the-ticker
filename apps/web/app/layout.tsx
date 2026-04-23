import type { Metadata } from "next";
import type { ReactNode } from "react";
import "../styles/globals.css";

export const metadata: Metadata = {
  title: "Learn the Ticker",
  description: "Citation-first beginner stock and ETF learning assistant"
};

export default function RootLayout({
  children
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <div className="app-shell">
          <header className="topbar">
            <a className="brand" href="/">
              Learn the Ticker
            </a>
            <nav aria-label="Primary navigation">
              <a href="/">Search</a>
              <a href="/compare?left=VOO&right=QQQ">Compare</a>
            </nav>
          </header>
          {children}
        </div>
      </body>
    </html>
  );
}
