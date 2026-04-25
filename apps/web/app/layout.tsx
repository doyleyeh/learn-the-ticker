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
          <header className="topbar" data-global-navigation-workflow="single-search-separate-compare">
            <a className="brand" href="/">
              Learn the Ticker
            </a>
            <nav aria-label="Primary navigation">
              <a href="/" data-nav-primary-entry="single-asset-search">
                Search
              </a>
              <a href="/compare" data-nav-secondary-entry="separate-comparison-workflow">
                Compare
              </a>
            </nav>
          </header>
          {children}
        </div>
      </body>
    </html>
  );
}
