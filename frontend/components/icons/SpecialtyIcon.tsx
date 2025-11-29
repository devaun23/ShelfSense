'use client';

interface SpecialtyIconProps {
  specialty: string;
  size?: number;
  className?: string;
}

export default function SpecialtyIcon({
  specialty,
  size = 16,
  className = '',
}: SpecialtyIconProps) {
  const iconProps = {
    width: size,
    height: size,
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 1.5,
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
    className,
  };

  switch (specialty) {
    case 'internal-medicine':
      // EKG/QRS wave
      return (
        <svg {...iconProps}>
          <path d="M2 12h4l2-6 3 12 2-6h2l1.5-3 1.5 3h4" />
        </svg>
      );

    case 'surgery':
      // Vertical closed scissors
      return (
        <svg {...iconProps}>
          <path d="M12 2l-3 6v5" />
          <path d="M12 2l3 6v5" />
          <circle cx="9" cy="18" r="3" />
          <circle cx="15" cy="18" r="3" />
          <path d="M9 13v2" />
          <path d="M15 13v2" />
        </svg>
      );

    case 'pediatrics':
      // Baby rattle
      return (
        <svg {...iconProps}>
          <circle cx="12" cy="7" r="5" />
          <path d="M12 12v6" />
          <path d="M10 18h4" />
          <circle cx="10" cy="6" r="1" fill="currentColor" />
          <circle cx="14" cy="6" r="1" fill="currentColor" />
          <circle cx="12" cy="9" r="1" fill="currentColor" />
        </svg>
      );

    case 'psychiatry':
      // Human head outline (profile)
      return (
        <svg {...iconProps}>
          <path d="M12 2C8 2 5 5 5 9c0 2.5 1.5 4.5 3 6 .5 1 1 2 1 3v2h6v-2c0-1 .5-2 1-3 1.5-1.5 3-3.5 3-6 0-4-3-7-7-7z" />
        </svg>
      );

    case 'obgyn':
      // Pregnant silhouette
      return (
        <svg {...iconProps}>
          <circle cx="12" cy="5" r="2.5" />
          <path d="M9 21v-4c0-2 1-4 3-4h.5c1.5 0 2.5 1.5 2.5 3 0 1.5-.5 3-2 4" />
          <ellipse cx="12" cy="13" rx="2.5" ry="3" />
        </svg>
      );

    case 'family-medicine':
      // Running person (exercise/wellness)
      return (
        <svg {...iconProps}>
          <circle cx="14" cy="4" r="2.5" />
          <path d="M7 22l4-8 3 3 4-7" />
          <path d="M11 14l-4-2" />
          <path d="M17 8l-3 5" />
        </svg>
      );

    case 'emergency-medicine':
      // First aid cross
      return (
        <svg {...iconProps}>
          <rect x="3" y="3" width="18" height="18" rx="2" />
          <path d="M12 8v8" strokeWidth="2.5" />
          <path d="M8 12h8" strokeWidth="2.5" />
        </svg>
      );

    case 'neurology':
      // Brain with hemispheres and folds
      return (
        <svg {...iconProps}>
          {/* Left hemisphere */}
          <path d="M12 4c-1.5 0-3 .5-4 1.5C6.5 7 6 8.5 6 10c0 1 .3 2 .8 2.8-.3.8-.5 1.5-.3 2.2.3 1.5 1.5 2.5 3 3 .5 1.5 1.5 2.5 2.5 2.5" />
          {/* Right hemisphere */}
          <path d="M12 4c1.5 0 3 .5 4 1.5 1.5 1.5 2 3 2 4.5 0 1-.3 2-.8 2.8.3.8.5 1.5.3 2.2-.3 1.5-1.5 2.5-3 3-.5 1.5-1.5 2.5-2.5 2.5" />
          {/* Brain stem */}
          <path d="M10 20.5c0 1 1 1.5 2 1.5s2-.5 2-1.5" />
          {/* Folds/gyri */}
          <path d="M8 8c1 .5 2 .5 3 0" />
          <path d="M13 8c1 .5 2 .5 3 0" />
          <path d="M7.5 12c1.5 0 2.5-.5 3.5-.5" />
          <path d="M13 11.5c1 0 2.5.5 4 .5" />
        </svg>
      );

    case 'step2-ck':
      // Open book (comprehensive study)
      return (
        <svg {...iconProps}>
          <path d="M2 5c2-1 4-1.5 6-1.5s4 .5 4 2v14c-1-.5-2.5-1-4-1s-4 .5-6 1.5V5z" />
          <path d="M12 5.5c0-1.5 2-2 4-2s4 .5 6 1.5v15c-2-1-4-1.5-6-1.5s-3 .5-4 1V5.5z" />
          <path d="M12 5.5v14" />
        </svg>
      );

    default:
      // Default medical cross
      return (
        <svg {...iconProps}>
          <path d="M12 4v16" />
          <path d="M4 12h16" />
        </svg>
      );
  }
}
