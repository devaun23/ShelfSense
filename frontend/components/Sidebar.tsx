'use client';

import { useState } from 'react';

interface SidebarProps {
  isOpen: boolean;
  onToggle: () => void;
}

const clerkships = [
  { name: 'Internal Medicine', available: true },
  { name: 'Surgery', available: false },
  { name: 'Pediatrics', available: false },
  { name: 'Obstetrics & Gynecology', available: false },
  { name: 'Family Medicine', available: false },
  { name: 'Emergency Medicine', available: false },
  { name: 'Neurology', available: false },
  { name: 'Psychiatry', available: false },
];

export default function Sidebar({ isOpen, onToggle }: SidebarProps) {
  const [selectedSpecialty, setSelectedSpecialty] = useState<string>('Internal Medicine');

  return (
    <>
      {/* Sidebar */}
      <div
        className={`fixed left-0 top-0 h-full bg-black border-r border-gray-800 transition-all duration-300 z-50 ${
          isOpen ? 'w-64' : 'w-0'
        } overflow-hidden`}
      >
        <div className="p-6 pt-16">
          <div className={`mb-8 transition-all duration-300 ${isOpen ? 'ml-8' : 'ml-0'}`}>
            <h2 className="text-xl font-semibold" style={{ fontFamily: 'var(--font-cormorant)' }}>
              ShelfSense
            </h2>
          </div>

          <nav className="space-y-3">
            {/* Step 2 CK Header */}
            <div className="px-3 py-2">
              <h3 className="text-lg font-semibold text-white" style={{ fontFamily: 'var(--font-cormorant)' }}>
                Step 2 CK
              </h3>
            </div>

            {/* Clerkships Section */}
            <div className="border-t border-gray-800 pt-3">
              <div className="px-3 pb-2">
                <p className="text-sm text-gray-500 uppercase tracking-wide">Clerkships</p>
              </div>

              <div className="space-y-1">
                {clerkships.map((clerkship) => (
                  <button
                    key={clerkship.name}
                    onClick={() => clerkship.available && setSelectedSpecialty(clerkship.name)}
                    disabled={!clerkship.available}
                    className={`w-full text-left px-3 py-2 rounded transition-colors ${
                      clerkship.available
                        ? selectedSpecialty === clerkship.name
                          ? 'bg-gray-900 text-white'
                          : 'text-gray-400 hover:text-white hover:bg-gray-900'
                        : 'text-gray-700 cursor-not-allowed'
                    }`}
                    style={{ fontFamily: 'var(--font-cormorant)' }}
                  >
                    {clerkship.name}
                    {!clerkship.available && (
                      <span className="ml-2 text-xs text-gray-600">(Coming Soon)</span>
                    )}
                  </button>
                ))}
              </div>
            </div>
          </nav>
        </div>
      </div>

      {/* Toggle Button - Thicker and more visible */}
      <button
        onClick={onToggle}
        className="fixed left-4 top-4 z-[60] px-3 py-2 text-gray-300 hover:text-white transition-colors text-2xl font-bold"
        style={{ lineHeight: '1' }}
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
