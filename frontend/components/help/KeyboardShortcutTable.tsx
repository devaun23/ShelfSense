'use client';

interface Shortcut {
  keys: string[];
  description: string;
}

const SHORTCUTS: Shortcut[] = [
  { keys: ['A', 'B', 'C', 'D', 'E'], description: 'Select answer choice' },
  { keys: ['Enter'], description: 'Submit answer' },
  { keys: ['N'], description: 'Next question (after feedback)' },
  { keys: ['Esc'], description: 'Close sidebar' },
];

export default function KeyboardShortcutTable() {
  return (
    <div className="overflow-hidden rounded-xl border border-gray-800">
      <table className="w-full">
        <thead>
          <tr className="bg-gray-900/50">
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Key
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Action
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-800">
          {SHORTCUTS.map((shortcut, index) => (
            <tr key={index} className="hover:bg-gray-900/30 transition-colors">
              <td className="px-4 py-3">
                <div className="flex gap-1.5 flex-wrap">
                  {shortcut.keys.map((key, i) => (
                    <span key={i}>
                      <kbd className="px-2 py-1 text-xs font-mono bg-gray-800 text-gray-300 rounded border border-gray-700">
                        {key}
                      </kbd>
                      {i < shortcut.keys.length - 1 && shortcut.keys.length > 1 && (
                        <span className="text-gray-600 mx-1">/</span>
                      )}
                    </span>
                  ))}
                </div>
              </td>
              <td className="px-4 py-3 text-sm text-gray-400">
                {shortcut.description}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
