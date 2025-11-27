'use client';

interface HelpSectionProps {
  id: string;
  title: string;
  children: React.ReactNode;
}

export default function HelpSection({ id, title, children }: HelpSectionProps) {
  return (
    <section id={id} className="scroll-mt-24">
      <h2
        className="text-2xl font-semibold text-white mb-4"
        style={{ fontFamily: 'var(--font-serif)' }}
      >
        {title}
      </h2>
      <div className="text-gray-300 leading-relaxed">
        {children}
      </div>
    </section>
  );
}
