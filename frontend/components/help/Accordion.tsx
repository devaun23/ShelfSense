'use client';

import { useState, useMemo } from 'react';
import AccordionItem from './AccordionItem';

export interface FAQItem {
  id: string;
  question: string;
  answer: React.ReactNode;
  category: 'scoring' | 'study' | 'account';
}

interface AccordionProps {
  items: FAQItem[];
  searchQuery?: string;
}

const CATEGORY_LABELS: Record<string, string> = {
  scoring: 'Scoring & Analytics',
  study: 'Study Features',
  account: 'Account & Technical',
};

export default function Accordion({ items, searchQuery = '' }: AccordionProps) {
  const [openIds, setOpenIds] = useState<Set<string>>(new Set());

  const toggleItem = (id: string) => {
    setOpenIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const expandAll = () => {
    setOpenIds(new Set(filteredItems.map((item) => item.id)));
  };

  const collapseAll = () => {
    setOpenIds(new Set());
  };

  // Filter items based on search query
  const filteredItems = useMemo(() => {
    if (!searchQuery.trim()) return items;

    const query = searchQuery.toLowerCase();
    return items.filter(
      (item) =>
        item.question.toLowerCase().includes(query) ||
        (typeof item.answer === 'string' && item.answer.toLowerCase().includes(query))
    );
  }, [items, searchQuery]);

  // Group by category
  const groupedItems = useMemo(() => {
    const groups: Record<string, FAQItem[]> = {};
    filteredItems.forEach((item) => {
      if (!groups[item.category]) {
        groups[item.category] = [];
      }
      groups[item.category].push(item);
    });
    return groups;
  }, [filteredItems]);

  if (filteredItems.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No FAQs match your search. Try a different term.
      </div>
    );
  }

  return (
    <div>
      {/* Expand/Collapse Controls */}
      <div className="flex justify-end gap-3 mb-4">
        <button
          onClick={expandAll}
          className="text-xs text-gray-500 hover:text-white transition-colors"
        >
          Expand all
        </button>
        <span className="text-gray-700">|</span>
        <button
          onClick={collapseAll}
          className="text-xs text-gray-500 hover:text-white transition-colors"
        >
          Collapse all
        </button>
      </div>

      {/* Grouped FAQs */}
      {Object.entries(groupedItems).map(([category, categoryItems]) => (
        <div key={category} className="mb-6">
          <h3 className="text-xs text-gray-600 font-medium uppercase tracking-wider mb-3">
            {CATEGORY_LABELS[category] || category}
          </h3>
          <div className="space-y-2">
            {categoryItems.map((item) => (
              <AccordionItem
                key={item.id}
                id={item.id}
                question={item.question}
                isOpen={openIds.has(item.id)}
                onToggle={() => toggleItem(item.id)}
                searchQuery={searchQuery}
              >
                {item.answer}
              </AccordionItem>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
