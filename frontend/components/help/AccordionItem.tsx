'use client';

interface AccordionItemProps {
  id: string;
  question: string;
  isOpen: boolean;
  onToggle: () => void;
  children: React.ReactNode;
  searchQuery?: string;
}

export default function AccordionItem({
  id,
  question,
  isOpen,
  onToggle,
  children,
  searchQuery = '',
}: AccordionItemProps) {
  // Highlight matching text in question
  const highlightText = (text: string) => {
    if (!searchQuery.trim()) return text;

    const regex = new RegExp(`(${searchQuery.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    const parts = text.split(regex);

    return parts.map((part, i) =>
      regex.test(part) ? (
        <mark key={i} className="bg-[#4169E1]/30 text-white rounded px-0.5">
          {part}
        </mark>
      ) : (
        part
      )
    );
  };

  return (
    <div className="border border-gray-800 rounded-xl overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full px-5 py-4 flex items-center justify-between hover:bg-gray-900/50 transition-colors text-left focus:outline-none focus:ring-2 focus:ring-[#4169E1] focus:ring-inset"
        aria-expanded={isOpen}
        aria-controls={`faq-content-${id}`}
        id={`faq-header-${id}`}
      >
        <span className="text-white text-sm font-medium pr-4">
          {highlightText(question)}
        </span>
        <svg
          className={`w-5 h-5 text-gray-500 flex-shrink-0 transition-transform duration-200 ${
            isOpen ? 'rotate-180' : ''
          }`}
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      <div
        id={`faq-content-${id}`}
        role="region"
        aria-labelledby={`faq-header-${id}`}
        className={`overflow-hidden transition-all duration-200 ${
          isOpen ? 'max-h-96' : 'max-h-0'
        }`}
      >
        <div className="px-5 pb-4 text-gray-400 text-sm leading-relaxed border-t border-gray-800 pt-4">
          {children}
        </div>
      </div>
    </div>
  );
}
