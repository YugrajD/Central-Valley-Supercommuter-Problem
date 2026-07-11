import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ALTAMONT — SJ County Transit Equity",
  description:
    "Test a proposed transit change in San Joaquin County and see how many more Bay Area jobs it puts within reach.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
