import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PRANAV — Personal Resource & Asset Navigator for Abundant Value",
  description:
    "Self-hostable personal finance app. See where your money is going before it goes there.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
