'use client';

import { forwardRef } from 'react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'warning' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  rounded?: 'default' | 'full';
  isLoading?: boolean;
  children: React.ReactNode;
}

const variantStyles = {
  primary: 'bg-[#4169E1] hover:bg-[#5B7FE8] text-white focus:ring-[#4169E1]',
  secondary: 'bg-gray-900 border border-gray-800 text-white hover:border-gray-700 hover:bg-gray-800 focus:ring-gray-600',
  danger: 'bg-red-500/20 text-red-400 hover:bg-red-500/30 focus:ring-red-500',
  warning: 'bg-amber-500/20 text-amber-400 hover:bg-amber-500/30 focus:ring-amber-500',
  ghost: 'text-gray-400 hover:text-white hover:bg-gray-900 focus:ring-gray-500',
};

const sizeStyles = {
  sm: 'px-3 py-1.5 text-sm gap-1.5',
  md: 'px-4 py-2.5 text-sm gap-2',
  lg: 'px-6 py-3 text-base gap-2',
};

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      rounded = 'default',
      isLoading = false,
      disabled,
      className = '',
      children,
      ...props
    },
    ref
  ) => {
    const roundedClass = rounded === 'full' ? 'rounded-full' : 'rounded-lg';

    const baseStyles = [
      'inline-flex items-center justify-center font-medium transition-all',
      'focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-black',
      'disabled:opacity-50 disabled:cursor-not-allowed',
      variantStyles[variant],
      sizeStyles[size],
      roundedClass,
      className,
    ].join(' ');

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={baseStyles}
        {...props}
      >
        {isLoading && (
          <svg
            className="w-4 h-4 animate-spin"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        )}
        {children}
      </button>
    );
  }
);

Button.displayName = 'Button';

export { Button };
