import type { Metadata } from "next";
import "@fontsource-variable/inter";
import "./globals.css";

export const metadata: Metadata = {
  title: "FMT",
  description: "Football Manager 26 club companion — live squad, development decisions.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="fmt-shell">{children}</body>
    </html>
  );
}
