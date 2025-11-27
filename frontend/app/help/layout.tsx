import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Help Center - ShelfSense',
  description: 'Get help with ShelfSense, the adaptive learning platform for USMLE Step 2 CK and Shelf exam preparation. Find answers to FAQs, learn about study modes, keyboard shortcuts, and analytics.',
  keywords: ['USMLE', 'Step 2 CK', 'Shelf exam', 'medical education', 'study help', 'FAQ'],
  openGraph: {
    title: 'Help Center - ShelfSense',
    description: 'Everything you need to know about using ShelfSense for USMLE Step 2 CK preparation.',
    type: 'website',
  },
};

export default function HelpLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
