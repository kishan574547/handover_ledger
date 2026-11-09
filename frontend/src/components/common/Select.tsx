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
      {label && <label className="text-xs font-medium text-slate-700">{label}</label>}
      <div className="relative">
        <select
          className={`w-full appearance-none rounded-lg border border-slate-300 bg-white px-3 py-2 pr-8 text-sm text-slate-800 shadow-sm focus:border-navy focus:outline-none focus:ring-1 focus:ring-navy disabled:bg-slate-50 disabled:text-slate-400 ${className}`}
          {...props}
        >
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
      </div>
      {helperText && <p className="text-xs text-slate-500">{helperText}</p>}
    </div>
  );
};
