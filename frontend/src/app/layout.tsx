import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FinTrust AI | Financial Evidence Workspace",
  description:
    "Evidence verification, PO-reconciliation, and fraud prevention for Indian MSMEs.",
  icons: {
    icon: "/icon.svg",
    shortcut: "/icon.svg",
    apple: "/icon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
