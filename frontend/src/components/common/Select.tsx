import React, { SelectHTMLAttributes } from 'react';
import { ChevronDown } from 'lucide-react';

interface Option {
  value: string | number;
  label: string;
}

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  options: Option[];
  helperText?: string;
}

export const Select: React.FC<SelectProps> = ({
  label,
  options,
  helperText,
  className = '',
  ...props
}) => {
  return (
    <div className="flex flex-col gap-1 text-left">
      {label && <label className="text-xs font-medium text-text-main">{label}</label>}
      <div className="relative">
        <select
          className={`w-full appearance-none rounded-btn border border-border bg-surface px-3 py-2 pr-8 text-sm text-text-main shadow-soft focus:border-navy dark:focus:border-teal focus:outline-none focus:ring-1 focus:ring-navy dark:focus:ring-teal disabled:opacity-50 disabled:cursor-not-allowed ${className}`}
          {...props}
        >
          {options.map((opt) => (
            <option key={opt.value} value={opt.value} className="bg-surface text-text-main">
              {opt.label}
            </option>
          ))}
        </select>
        <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
      </div>
      {helperText && <p className="text-xs text-text-muted">{helperText}</p>}
    </div>
  );
};
