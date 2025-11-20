'use client';

import { useState } from 'react';

interface SidebarProps {
  isOpen: boolean;
  onToggle: () => void;
}

const specialties = [
  'Internal Medicine',
  'Surgery',
  'Pediatrics',
  'Obstetrics & Gynecology',
  'Family Medicine',
  'Emergency Medicine',
  'Neurology',
  'Psychiatry',
];

export default function Sidebar({ isOpen, onToggle }: SidebarProps) {
  const [selectedSpecialty, setSelectedSpecialty] = useState<string | null>(null);

  return (
    <>
      {/* Sidebar */}
      <div
        className={`fixed left-0 top-0 h-full bg-black border-r border-gray-800 transition-all duration-300 z-50 ${
          isOpen ? 'w-64' : 'w-0'
        } overflow-hidden`}
      >
        <div className="p-6">
          <div className="mb-8">
            <h2 className="text-xl font-semibold">ShelfSense</h2>
          </div>

          <nav className="space-y-1">
            <button
              onClick={() => setSelectedSpecialty(null)}
              className={`w-full text-left px-3 py-2 rounded transition-colors ${
                selectedSpecialty === null
                  ? 'bg-gray-900 text-white'
                  : 'text-gray-400 hover:text-white hover:bg-gray-900'
              }`}
            >
              All Questions
            </button>

            {specialties.map((specialty) => (
              <button
                key={specialty}
                onClick={() => setSelectedSpecialty(specialty)}
                className={`w-full text-left px-3 py-2 rounded transition-colors ${
                  selectedSpecialty === specialty
                    ? 'bg-gray-900 text-white'
                    : 'text-gray-400 hover:text-white hover:bg-gray-900'
                }`}
              >
                {specialty}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Toggle Button */}
      <button
        onClick={onToggle}
        className="fixed left-4 top-4 z-50 px-3 py-2 text-gray-400 hover:text-white transition-colors"
      >
        {isOpen ? '←' : '→'}
      </button>

      {/* Overlay when sidebar is open (mobile) */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-40 md:hidden"
          onClick={onToggle}
        />
      )}
    </>
  );
}
