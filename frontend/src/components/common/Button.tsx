import React, { ButtonHTMLAttributes } from 'react';
import { Loader2 } from 'lucide-react';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'accent' | 'outline' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  isIconOnly?: boolean;
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  isIconOnly = false,
  isLoading = false,
  leftIcon,
  rightIcon,
  className = '',
  disabled,
  ...props
}) => {
  // Base styles: 10px radius, visible 2px focus ring, active scale, transition, no-select
  const baseStyles =
    'inline-flex items-center justify-center font-medium rounded-btn transition-all duration-150 ' +
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-navy ' +
    'dark:focus-visible:ring-offset-slate-900 dark:focus-visible:ring-teal ' +
    'disabled:opacity-50 disabled:pointer-events-none disabled:cursor-not-allowed select-none active:scale-[0.98]';

  // Height and padding according to spec:
  // sm: 36px (h-9), md: 40px (h-10), lg: 48px (h-12)
  // Below 1024px (touch), minimum 44px touch target enforced via min-h-[44px]
  const sizeStyles = {
    sm: isIconOnly
      ? 'w-9 h-9 min-w-[44px] min-h-[44px] lg:min-w-[36px] lg:min-h-[36px] p-0 text-xs'
      : 'h-9 min-h-[44px] lg:min-h-[36px] px-3 text-xs gap-1.5',
    md: isIconOnly
      ? 'w-10 h-10 min-w-[44px] min-h-[44px] lg:min-w-[40px] lg:min-h-[40px] p-0 text-sm'
      : 'h-10 min-h-[44px] lg:min-h-[40px] px-4 text-sm gap-2',
    lg: isIconOnly
      ? 'w-12 h-12 min-w-[48px] min-h-[48px] p-0 text-base'
      : 'h-12 min-h-[48px] px-5 text-base gap-2.5',
  };

  const variantStyles = {
    primary:
      'bg-navy text-white hover:bg-navy-hover dark:bg-navy-dark dark:hover:bg-navy shadow-sm',
    secondary:
      'bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-100 hover:bg-slate-200 dark:hover:bg-slate-700 border border-border shadow-soft',
    accent:
      'bg-teal text-white hover:bg-teal-hover shadow-sm',
    outline:
      'border border-border bg-surface text-text-main hover:bg-slate-50 dark:hover:bg-slate-800/60 shadow-soft',
    ghost:
      'text-text-muted hover:text-text-main hover:bg-slate-100 dark:hover:bg-slate-800/60',
    danger:
      'bg-rose-600 text-white hover:bg-rose-700 shadow-sm',
  };

  return (
    <button
      className={`${baseStyles} ${sizeStyles[size]} ${variantStyles[variant]} ${className}`}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? (
        <Loader2 className="w-4 h-4 animate-spin text-current" />
      ) : (
        leftIcon && <span className="flex-shrink-0">{leftIcon}</span>
      )}
      {children && <span className="truncate">{children}</span>}
      {!isLoading && rightIcon && <span className="flex-shrink-0">{rightIcon}</span>}
    </button>
  );
};
