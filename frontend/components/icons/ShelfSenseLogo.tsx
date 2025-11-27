interface ShelfSenseLogoProps {
  size?: number;
  className?: string;
  animate?: boolean;
  color?: string;
}

export default function ShelfSenseLogo({
  size = 32,
  className = '',
  animate = true,
  color = '#4169E1',
}: ShelfSenseLogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      className={`${animate ? 'logo-breathe' : ''} ${className}`}
      style={{ display: 'block' }}
    >
      <path
        d="M8 6 C20 6, 12 16, 24 16 C12 16, 20 26, 8 26"
        stroke={color}
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
    </svg>
  );
}
