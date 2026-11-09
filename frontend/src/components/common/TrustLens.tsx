import React from 'react';
import { ShieldCheck, Sparkles, Layers, Info } from 'lucide-react';
import { ClaimStatus } from '../../types';

export type TrustLensMode = 'proven_only' | 'proven_inferred' | 'everything';

interface TrustLensProps {
  mode: TrustLensMode;
  onChange: (mode: TrustLensMode) => void;
  totalCount: number;
  filteredCount: number;
  className?: string;
  showLegend?: boolean;
}

export function filterClaimsByTrustLens<T extends { status: ClaimStatus }>(
  items: T[],
  mode: TrustLensMode
): T[] {
  if (mode === 'proven_only') {
    return items.filter((item) => item.status === 'verified');
  }
  if (mode === 'proven_inferred') {
    return items.filter((item) => item.status === 'verified' || item.status === 'inferred');
  }
  return items;
}

export const TrustLens: React.FC<TrustLensProps> = ({
  mode,
  onChange,
  totalCount,
  filteredCount,
  className = '',
  showLegend = true,
}) => {
  const options: { id: TrustLensMode; label: string; icon: React.ReactNode; desc: string }[] = [
    {
      id: 'proven_only',
      label: 'Proven Only',
      icon: <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />,
      desc: 'Only strictly verified claims backed by exact verbatim source passages.',
    },
    {
      id: 'proven_inferred',
      label: 'Proven + Inferred',
      icon: <Sparkles className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />,
      desc: 'Verified claims plus AI/leaver-inferred knowledge.',
    },
    {
      id: 'everything',
      label: 'Everything',
      icon: <Layers className="w-3.5 h-3.5 text-navy dark:text-teal" />,
      desc: 'All recorded items including conflicts and gaps.',
    },
  ];

  return (
    <div
      className={`flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-2.5 sm:p-3 rounded-card bg-surface border border-border shadow-soft ${className}`}
    >
      {/* Left: Trust Lens Segmented Switcher */}
      <div className="flex items-center gap-2 overflow-x-auto no-scrollbar">
        <span className="text-[11px] font-bold uppercase tracking-wider text-text-muted flex items-center gap-1.5 flex-shrink-0 px-1">
          <ShieldCheck className="w-4 h-4 text-navy dark:text-teal" />
          <span>Trust Lens:</span>
        </span>

        <div className="flex items-center bg-slate-100 dark:bg-slate-800/80 p-0.5 rounded-btn border border-border">
          {options.map((opt) => {
            const isSelected = mode === opt.id;
            return (
              <button
                key={opt.id}
                onClick={() => onChange(opt.id)}
                title={opt.desc}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-btn text-xs font-medium transition-all min-h-[36px] select-none ${
                  isSelected
                    ? 'bg-surface text-text-main font-semibold shadow-soft border border-border'
                    : 'text-text-muted hover:text-text-main hover:bg-slate-200/50 dark:hover:bg-slate-700/50'
                }`}
              >
                {opt.icon}
                <span className="whitespace-nowrap">{opt.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Right: Live Item Count & Legend */}
      <div className="flex items-center justify-between sm:justify-end gap-3 text-xs">
        <div className="font-medium text-text-main bg-slate-100 dark:bg-slate-800 px-2.5 py-1 rounded-btn border border-border">
          Showing <strong className="text-navy dark:text-teal font-bold">{filteredCount}</strong> of{' '}
          <span className="text-text-muted">{totalCount}</span> items
        </div>

        {showLegend && (
          <div className="hidden lg:flex items-center gap-2 text-[11px] text-text-muted">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-status-verified-text" /> Verified
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-status-inferred-text" /> Inferred
            </span>
            {mode === 'everything' && (
              <>
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-status-conflicting-text" /> Conflicting
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-status-missing-text" /> Missing
                </span>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

