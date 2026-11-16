import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FinTrust AI | Overview",
  description:
    "Evidence verification and fraud prevention for Indian MSMEs.",
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
