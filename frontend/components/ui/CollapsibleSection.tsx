'use client';

import React, { memo, useState } from 'react';

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
        className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-950 transition-colors"
      >
        <div className="flex items-center gap-3">
          <h3 className="text-base font-medium text-white">{title}</h3>
          {badge}
        </div>
        <svg
          className={`w-5 h-5 text-gray-500 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {isOpen && (
        <div className="px-6 pb-6 border-t border-gray-800">
          {children}
        </div>
      )}
    </div>
  );
});

export default CollapsibleSection;
