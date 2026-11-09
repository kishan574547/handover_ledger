import React from 'react';
import { CheckCircle2, Loader2, AlertCircle, Circle } from 'lucide-react';
import { StepProgress } from '../../types';

interface StepperProps {
  steps: StepProgress[];
  currentPercent: number;
  overallStatus: string;
}

export const Stepper: React.FC<StepperProps> = ({ steps, currentPercent, overallStatus }) => {
  return (
    <div className="w-full space-y-4">
      {/* Progress Bar */}
      <div>
        <div className="flex justify-between items-center text-xs font-medium text-text-muted mb-1.5">
          <span>{overallStatus}</span>
          <span className="font-semibold text-navy dark:text-teal">{currentPercent}%</span>
        </div>
        <div className="w-full h-2.5 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden border border-border">
          <div
            className="h-full bg-navy dark:bg-teal transition-all duration-300 rounded-full"
            style={{ width: `${Math.min(100, Math.max(0, currentPercent))}%` }}
          />
        </div>
      </div>

      {/* Steps List */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
        {steps.map((step, idx) => {
          const isDone = step.status === 'completed';
          const isInProgress = step.status === 'in_progress';
          const isFailed = step.status === 'failed';

          return (
            <div
              key={idx}
              className={`flex items-start gap-3 p-3 rounded-lg border transition-all ${
                isInProgress
                  ? 'bg-blue-50/60 dark:bg-blue-950/40 border-blue-200 dark:border-blue-800 shadow-sm'
                  : isDone
                  ? 'bg-emerald-50/40 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800'
                  : isFailed
                  ? 'bg-rose-50 dark:bg-rose-950/40 border-rose-200 dark:border-rose-800'
                  : 'bg-slate-50 dark:bg-slate-900/40 border-border opacity-60'
              }`}
            >
              <div className="flex-shrink-0 mt-0.5">
                {isDone && <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />}
                {isInProgress && <Loader2 className="w-4 h-4 text-blue-600 dark:text-blue-400 animate-spin" />}
                {isFailed && <AlertCircle className="w-4 h-4 text-rose-600 dark:text-rose-400" />}
                {!isDone && !isInProgress && !isFailed && (
                  <Circle className="w-4 h-4 text-slate-400 dark:text-slate-600" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-semibold text-text-main truncate">
                    {idx + 1}. {step.name}
                  </h4>
                  <span className="text-[10px] text-text-muted font-mono">{step.percent}%</span>
                </div>
                {step.details && (
                  <p className="text-[11px] text-text-muted mt-0.5 line-clamp-1">{step.details}</p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
