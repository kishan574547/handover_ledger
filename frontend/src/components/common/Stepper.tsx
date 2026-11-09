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
        <div className="flex justify-between items-center text-xs font-medium text-slate-600 mb-1.5">
          <span>{overallStatus}</span>
          <span className="font-semibold text-navy">{currentPercent}%</span>
        </div>
        <div className="w-full h-2.5 bg-slate-100 rounded-full overflow-hidden border border-slate-200">
          <div
            className="h-full bg-navy transition-all duration-300 rounded-full"
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
                  ? 'bg-blue-50/60 border-blue-200 shadow-sm'
                  : isDone
                  ? 'bg-emerald-50/40 border-emerald-200'
                  : isFailed
                  ? 'bg-rose-50 border-rose-200'
                  : 'bg-slate-50 border-slate-200 opacity-60'
              }`}
            >
              <div className="flex-shrink-0 mt-0.5">
                {isDone && <CheckCircle2 className="w-4 h-4 text-emerald-600" />}
                {isInProgress && <Loader2 className="w-4 h-4 text-blue-600 animate-spin" />}
                {isFailed && <AlertCircle className="w-4 h-4 text-rose-600" />}
                {!isDone && !isInProgress && !isFailed && (
                  <Circle className="w-4 h-4 text-slate-400" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-semibold text-slate-800 truncate">
                    {idx + 1}. {step.name}
                  </h4>
                  <span className="text-[10px] text-slate-500 font-mono">{step.percent}%</span>
                </div>
                {step.details && (
                  <p className="text-[11px] text-slate-600 mt-0.5 line-clamp-1">{step.details}</p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

