// Specialty configuration for ShelfSense MVP
// All 8 shelf specialties + Step 2 CK Full Prep mode

export interface Specialty {
  id: string;
  name: string;
  apiName: string; // Name to send to backend API
  slug: string; // URL-friendly slug for portal routes
  description?: string; // Short description for portal dashboard
  icon?: string; // Emoji or icon identifier
}

export const SPECIALTIES: Specialty[] = [
  {
    id: 'internal-medicine',
    name: 'Internal Medicine',
    apiName: 'Internal Medicine',
    slug: 'internal-medicine',
    description: 'Cardiology, Pulmonology, GI, Nephrology, Heme/Onc, Endocrine, Rheumatology, ID',
    icon: '🏥',
  },
  {
    id: 'surgery',
    name: 'Surgery',
    apiName: 'Surgery',
    slug: 'surgery',
    description: 'General Surgery, Trauma, Vascular, Surgical Emergencies',
    icon: '🔪',
  },
  {
    id: 'pediatrics',
    name: 'Pediatrics',
    apiName: 'Pediatrics',
    slug: 'pediatrics',
    description: 'Growth & Development, Pediatric Diseases, Neonatology',
    icon: '👶',
  },
  {
    id: 'psychiatry',
    name: 'Psychiatry',
    apiName: 'Psychiatry',
    slug: 'psychiatry',
    description: 'Mood Disorders, Psychosis, Anxiety, Substance Use, Therapy',
    icon: '🧠',
  },
  {
    id: 'ob-gyn',
    name: 'OB-GYN',
    apiName: 'Obstetrics and Gynecology',
    slug: 'ob-gyn',
    description: 'Pregnancy, Labor & Delivery, Gynecologic Conditions',
    icon: '🤰',
  },
  {
    id: 'family-medicine',
    name: 'Family Medicine',
    apiName: 'Family Medicine',
    slug: 'family-medicine',
    description: 'Preventive Care, Chronic Disease Management, All Ages',
    icon: '👨‍👩‍👧‍👦',
  },
  {
    id: 'emergency-medicine',
    name: 'Emergency Medicine',
    apiName: 'Emergency Medicine',
    slug: 'emergency-medicine',
    description: 'Trauma, Resuscitation, Acute Care, Toxicology',
    icon: '🚨',
  },
  {
    id: 'neurology',
    name: 'Neurology',
    apiName: 'Neurology',
    slug: 'neurology',
    description: 'Stroke, Seizures, Headache, Neuromuscular, Dementia',
    icon: '🧬',
  },
];

// Step 2 CK Full Prep mode - mixed questions from all specialties
export const FULL_PREP_MODE: Specialty = {
  id: 'step2-ck',
  name: 'Step 2 CK Full Prep',
  apiName: '', // Empty means no specialty filter - gets mixed questions
  slug: 'step2-ck',
  description: 'Mixed practice across all specialties for comprehensive Step 2 CK prep',
  icon: '📚',
};

// All portals including full prep mode
export const ALL_PORTALS: Specialty[] = [...SPECIALTIES, FULL_PREP_MODE];

// Helper function to get specialty by ID
export function getSpecialtyById(id: string): Specialty | null {
  if (id === 'step2-ck') return FULL_PREP_MODE;
  return SPECIALTIES.find(s => s.id === id) || null;
}

// Helper function to get specialty by API name
export function getSpecialtyByApiName(apiName: string): Specialty | null {
  return SPECIALTIES.find(s => s.apiName.toLowerCase() === apiName.toLowerCase()) || null;
}

// Helper function to get specialty by slug (for portal routes)
export function getSpecialtyBySlug(slug: string): Specialty | null {
  if (slug === 'step2-ck') return FULL_PREP_MODE;
  return SPECIALTIES.find(s => s.slug === slug) || null;
}

// Check if a slug is valid
export function isValidPortalSlug(slug: string): boolean {
  return ALL_PORTALS.some(p => p.slug === slug);
}
