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
      // Horizontal open scissors (classic design)
      return (
        <svg {...iconProps}>
          {/* Finger loops on left */}
          <circle cx="5" cy="8" r="2.5" />
          <circle cx="5" cy="16" r="2.5" />
          {/* Handles */}
          <path d="M7.5 8h3" />
          <path d="M7.5 16h3" />
          {/* Pivot point */}
          <circle cx="11" cy="12" r="1" fill="currentColor" />
          {/* Blades pointing right */}
          <path d="M11 12l10-4" />
          <path d="M11 12l10 4" />
        </svg>
      );

    case 'pediatrics':
      // Balloon with wavy string
      return (
        <svg {...iconProps}>
          {/* Balloon */}
          <ellipse cx="12" cy="8" rx="5" ry="6" />
          {/* Knot */}
          <path d="M11 14l2 0" />
          <path d="M12 14v1" />
          {/* Wavy string */}
          <path d="M12 15c-1.5 1.5 1.5 3 0 4.5-1.5 1.5 1.5 3 0 4.5" />
        </svg>
      );

    case 'psychiatry':
      // Accurate human head profile (side view)
      return (
        <svg {...iconProps}>
          {/* Head profile outline */}
          <path d="M9 3c-3 0-5 2.5-5 6 0 1.5.5 3 1.5 4l-1 2v3c0 1 .5 1.5 1.5 1.5h2c.5 0 1 .5 1 1v1.5h4v-1.5c0-.5.5-1 1-1h.5c1 0 2-.5 2.5-1.5.5-1 1-2.5 1-4 0-2-.5-4-2-5.5C13.5 4 11 3 9 3z" />
          {/* Ear */}
          <path d="M18 11c.5 0 1 .5 1 1.5s-.5 1.5-1 1.5" />
        </svg>
      );

    case 'obgyn':
      // Pregnant woman silhouette with hair (side profile)
      return (
        <svg {...iconProps}>
          {/* Head */}
          <circle cx="10" cy="4" r="2" />
          {/* Hair flowing */}
          <path d="M8 3c-1.5 1-2 3-2 5" />
          <path d="M9 2.5c-1 1.5-1.5 3.5-1 6" />
          <path d="M10 2c-.5 2-1 4-.5 6" />
          {/* Neck */}
          <path d="M10 6v1" />
          {/* Back curve */}
          <path d="M10 7c-1 1-1.5 3-1.5 5 0 2 .5 4 1 6" />
          {/* Front with pregnant belly */}
          <path d="M10 7c1 0 2 1.5 3 4 1 2.5 1 5 0 7" />
          {/* Feet */}
          <path d="M9.5 18h4" />
        </svg>
      );

    case 'family-medicine':
      // Running person outline
      return (
        <svg {...iconProps}>
          {/* Head */}
          <circle cx="14" cy="4" r="2" />
          {/* Torso */}
          <path d="M12 8l2-2" />
          <path d="M14 6l-2 6" />
          {/* Arms */}
          <path d="M12 8l-4 2" />
          <path d="M12 10l4-1" />
          {/* Back leg */}
          <path d="M12 12l-3 5-2 4" />
          {/* Front leg */}
          <path d="M12 12l2 4 4 1" />
        </svg>
      );

    case 'emergency-medicine':
      // Emergency button (circle with cross)
      return (
        <svg {...iconProps}>
          {/* Outer circle (button) */}
          <circle cx="12" cy="12" r="9" />
          {/* Inner cross */}
          <path d="M12 7v10" strokeWidth="2.5" />
          <path d="M7 12h10" strokeWidth="2.5" />
        </svg>
      );

    case 'neurology':
      // Brain side profile with clear lobes and gyri
      return (
        <svg {...iconProps}>
          {/* Main brain outline - top curve */}
          <path d="M5 11c0-2 .5-4 2-5.5C8.5 4 10.5 3.5 12 3.5c2 0 4 1 5.5 2.5 1 1 1.5 2.5 1.5 4 0 1.5-.5 3-1.5 4-1 1-1.5 1.5-1.5 2.5v2c0 .5-.5 1-1 1h-2" />
          {/* Bottom curve and cerebellum area */}
          <path d="M5 11c-.5 1.5 0 3 1 4s2 1.5 2.5 2.5v1.5c0 .5.5 1 1 1h2" />
          {/* Cerebellum bumps */}
          <path d="M15 17c.5.3 1 .3 1.5 0" />
          <path d="M15.5 18.5c.5.3 1 .3 1.5 0" />
          {/* Gyri folds - top */}
          <path d="M7 7c1.5.5 3 .5 4.5 0" />
          <path d="M12.5 6c1.5.5 3 .5 4 0" />
          {/* Gyri folds - middle */}
          <path d="M6 10c2 .5 4 .5 5.5 0" />
          <path d="M12.5 10c2 .5 3.5 .3 5-.5" />
          {/* Gyri fold - lower */}
          <path d="M7 13c1.5.5 3 .5 4 0" />
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
