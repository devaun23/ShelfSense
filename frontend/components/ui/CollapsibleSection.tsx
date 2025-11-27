'use client';

import React, { memo, useState, useId } from 'react';

interface CollapsibleSectionProps {
  title: string;
  children: React.ReactNode;
  badge?: React.ReactNode;
  // Controlled mode (external state)
  isOpen?: boolean;
  onToggle?: () => void;
  // Uncontrolled mode (internal state)
  defaultOpen?: boolean;
}

const CollapsibleSection = memo(function CollapsibleSection({
  title,
  children,
  badge,
  isOpen: controlledIsOpen,
  onToggle,
  defaultOpen = false
}: CollapsibleSectionProps) {
  // Internal state for uncontrolled mode
  const [internalIsOpen, setInternalIsOpen] = useState(defaultOpen);

  // Generate unique IDs for ARIA
  const id = useId();
  const contentId = `${id}-content`;
  const headingId = `${id}-heading`;

  // Use controlled state if provided, otherwise use internal state
  const isControlled = controlledIsOpen !== undefined;
  const isOpen = isControlled ? controlledIsOpen : internalIsOpen;

  const handleToggle = () => {
    if (isControlled && onToggle) {
      onToggle();
    } else {
      setInternalIsOpen(prev => !prev);
    }
  };

  return (
    <div className="border border-gray-800 rounded-2xl overflow-hidden mb-4">
      <button
        onClick={handleToggle}
        aria-expanded={isOpen}
        aria-controls={contentId}
        className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-950 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#4169E1] focus-visible:ring-inset"
      >
        <div className="flex items-center gap-3">
          <h3 id={headingId} className="text-base font-medium text-white">{title}</h3>
          {badge}
        </div>
        <svg
          className={`w-5 h-5 text-gray-500 motion-safe:transition-transform motion-safe:duration-200 ${isOpen ? 'rotate-180' : ''}`}
          fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      <div
        id={contentId}
        role="region"
        aria-labelledby={headingId}
        className={`motion-safe:transition-all motion-safe:duration-200 ease-out overflow-hidden ${isOpen ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0'}`}
      >
        <div className="px-6 pb-6 border-t border-gray-800">
          {children}
        </div>
      </div>
    </div>
  );
});

export default CollapsibleSection;
