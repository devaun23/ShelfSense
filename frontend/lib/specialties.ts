// Specialty configuration for ShelfSense MVP
// All 8 shelf specialties + Step 2 CK Full Prep mode

export interface Specialty {
  id: string;
  name: string;
  shortName: string;
  apiName: string; // Name to send to backend API
  icon: string;
  color: string;
  bgColor: string;
  borderColor: string;
}

export const SPECIALTIES: Specialty[] = [
  {
    id: 'internal-medicine',
    name: 'Internal Medicine',
    shortName: 'IM',
    apiName: 'Internal Medicine',
    icon: '🫀',
    color: 'text-red-400',
    bgColor: 'bg-red-500/10',
    borderColor: 'border-red-500/30',
  },
  {
    id: 'surgery',
    name: 'Surgery',
    shortName: 'Surg',
    apiName: 'Surgery',
    icon: '🔪',
    color: 'text-blue-400',
    bgColor: 'bg-blue-500/10',
    borderColor: 'border-blue-500/30',
  },
  {
    id: 'pediatrics',
    name: 'Pediatrics',
    shortName: 'Peds',
    apiName: 'Pediatrics',
    icon: '👶',
    color: 'text-pink-400',
    bgColor: 'bg-pink-500/10',
    borderColor: 'border-pink-500/30',
  },
  {
    id: 'psychiatry',
    name: 'Psychiatry',
    shortName: 'Psych',
    apiName: 'Psychiatry',
    icon: '🧠',
    color: 'text-purple-400',
    bgColor: 'bg-purple-500/10',
    borderColor: 'border-purple-500/30',
  },
  {
    id: 'ob-gyn',
    name: 'OB-GYN',
    shortName: 'OB',
    apiName: 'Obstetrics and Gynecology',
    icon: '🤰',
    color: 'text-rose-400',
    bgColor: 'bg-rose-500/10',
    borderColor: 'border-rose-500/30',
  },
  {
    id: 'family-medicine',
    name: 'Family Medicine',
    shortName: 'FM',
    apiName: 'Family Medicine',
    icon: '🏠',
    color: 'text-green-400',
    bgColor: 'bg-green-500/10',
    borderColor: 'border-green-500/30',
  },
  {
    id: 'emergency-medicine',
    name: 'Emergency Medicine',
    shortName: 'EM',
    apiName: 'Emergency Medicine',
    icon: '🚑',
    color: 'text-orange-400',
    bgColor: 'bg-orange-500/10',
    borderColor: 'border-orange-500/30',
  },
  {
    id: 'neurology',
    name: 'Neurology',
    shortName: 'Neuro',
    apiName: 'Neurology',
    icon: '🧬',
    color: 'text-indigo-400',
    bgColor: 'bg-indigo-500/10',
    borderColor: 'border-indigo-500/30',
  },
];

// Step 2 CK Full Prep mode - mixed questions from all specialties
export const FULL_PREP_MODE: Specialty = {
  id: 'step2-ck',
  name: 'Step 2 CK Full Prep',
  shortName: 'Step 2',
  apiName: '', // Empty means no specialty filter - gets mixed questions
  icon: '📚',
  color: 'text-[#4169E1]',
  bgColor: 'bg-[#4169E1]/10',
  borderColor: 'border-[#4169E1]/30',
};

// Helper function to get specialty by ID
export function getSpecialtyById(id: string): Specialty | null {
  if (id === 'step2-ck') return FULL_PREP_MODE;
  return SPECIALTIES.find(s => s.id === id) || null;
}

// Helper function to get specialty by API name
export function getSpecialtyByApiName(apiName: string): Specialty | null {
  return SPECIALTIES.find(s => s.apiName.toLowerCase() === apiName.toLowerCase()) || null;
}
