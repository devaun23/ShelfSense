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
      // Heart with pulse line
      return (
        <svg {...iconProps}>
          <path d="M12 20s-7-5.5-7-10a4 4 0 0 1 7-2.5 4 4 0 0 1 7 2.5c0 4.5-7 10-7 10z" />
          <path d="M8 12h2l1-2 2 4 1-2h2" />
        </svg>
      );

    case 'surgery':
      // Scalpel
      return (
        <svg {...iconProps}>
          <path d="M4 20l12-12" />
          <path d="M16 8l-2-2c2-2 5-2 6-1s1 4-1 6l-2-2" />
          <path d="M12 12l-8 8" />
        </svg>
      );

    case 'pediatrics':
      // Child/baby outline
      return (
        <svg {...iconProps}>
          <circle cx="12" cy="6" r="3" />
          <path d="M9 21v-5a3 3 0 0 1 6 0v5" />
          <path d="M7 13l5 3 5-3" />
        </svg>
      );

    case 'psychiatry':
      // Brain with thought
      return (
        <svg {...iconProps}>
          <path d="M12 4.5a4.5 4.5 0 0 0-4.5 4.5c0 1.5.5 2.5 1.5 3.5l-1 5.5h8l-1-5.5c1-1 1.5-2 1.5-3.5a4.5 4.5 0 0 0-4.5-4.5z" />
          <path d="M9 7a2 2 0 0 1 3-1 2 2 0 0 1 3 1" />
          <path d="M10 18v2" />
          <path d="M14 18v2" />
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
      // House with heart
      return (
        <svg {...iconProps}>
          <path d="M3 10l9-7 9 7" />
          <path d="M5 10v10h14V10" />
          <path d="M12 13s-2 1-2 2.5a2 2 0 0 0 4 0c0-1.5-2-2.5-2-2.5z" />
        </svg>
      );

    case 'emergency-medicine':
      // Cross/plus in circle
      return (
        <svg {...iconProps}>
          <circle cx="12" cy="12" r="9" />
          <path d="M12 7v10" />
          <path d="M7 12h10" />
        </svg>
      );

    case 'neurology':
      // Brain outline
      return (
        <svg {...iconProps}>
          <path d="M12 4c-2 0-4 1.5-4 4 0 1.5.5 2.5 1.5 3.5-.5 1-1 2-1 3.5 0 2 1.5 4 3.5 4s3.5-2 3.5-4c0-1.5-.5-2.5-1-3.5 1-1 1.5-2 1.5-3.5 0-2.5-2-4-4-4z" />
          <path d="M10 8c1-.5 2-.5 3 0" />
          <path d="M9 12c1 .5 2.5.5 4 0" />
        </svg>
      );

    case 'step2-ck':
      // Book/exam
      return (
        <svg {...iconProps}>
          <path d="M4 4h16v16H4z" />
          <path d="M4 4l8 6 8-6" />
          <path d="M8 12h8" />
          <path d="M8 15h5" />
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
