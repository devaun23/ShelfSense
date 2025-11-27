'use client';

export interface BadgeProps {
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info' | 'purple';
  size?: 'sm' | 'md';
  children: React.ReactNode;
  className?: string;
}

const variantStyles = {
  default: 'bg-gray-800 text-gray-400',
  success: 'bg-emerald-500/10 text-emerald-400',
  warning: 'bg-amber-500/10 text-amber-400',
  danger: 'bg-red-500/10 text-red-400',
  info: 'bg-blue-500/10 text-blue-400',
  purple: 'bg-purple-500/10 text-purple-400',
};

const sizeStyles = {
  sm: 'px-1.5 py-0.5 text-xs',
  md: 'px-2 py-0.5 text-xs',
};

export function Badge({
  variant = 'default',
  size = 'md',
  className = '',
  children,
}: BadgeProps) {
  const baseStyles = [
    'rounded-full font-medium inline-flex items-center',
    variantStyles[variant],
    sizeStyles[size],
    className,
  ].join(' ');

  return <span className={baseStyles}>{children}</span>;
}
