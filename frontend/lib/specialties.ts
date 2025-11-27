// Specialty configuration for ShelfSense MVP
// All 8 shelf specialties + Step 2 CK Full Prep mode

export interface Specialty {
  id: string;
  name: string;
  apiName: string; // Name to send to backend API
}

export const SPECIALTIES: Specialty[] = [
  {
    id: 'internal-medicine',
    name: 'Internal Medicine',
    apiName: 'Internal Medicine',
  },
  {
    id: 'surgery',
    name: 'Surgery',
    apiName: 'Surgery',
  },
  {
    id: 'pediatrics',
    name: 'Pediatrics',
    apiName: 'Pediatrics',
  },
  {
    id: 'psychiatry',
    name: 'Psychiatry',
    apiName: 'Psychiatry',
  },
  {
    id: 'ob-gyn',
    name: 'OB-GYN',
    apiName: 'Obstetrics and Gynecology',
  },
  {
    id: 'family-medicine',
    name: 'Family Medicine',
    apiName: 'Family Medicine',
  },
  {
    id: 'emergency-medicine',
    name: 'Emergency Medicine',
    apiName: 'Emergency Medicine',
  },
  {
    id: 'neurology',
    name: 'Neurology',
    apiName: 'Neurology',
  },
];

// Step 2 CK Full Prep mode - mixed questions from all specialties
export const FULL_PREP_MODE: Specialty = {
  id: 'step2-ck',
  name: 'Step 2 CK Full Prep',
  apiName: '', // Empty means no specialty filter - gets mixed questions
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
