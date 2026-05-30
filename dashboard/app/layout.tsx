import "./globals.css";

export const metadata = {
  title: "FairBench — Integrity Audit",
  description: "Voice competency training with integrity auditing (synthetic data only)",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
