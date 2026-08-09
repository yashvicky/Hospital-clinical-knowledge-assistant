import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Hospital Clinical Knowledge Assistant',
  description: 'HIPAA-secure retrieval-augmented assistant for hospital clinical guidelines, SOPs, and drug manuals.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
