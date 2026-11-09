import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Compass,
  CheckCircle2,
  Circle,
  X,
  ChevronRight,
} from 'lucide-react';
import { ProgressRing } from './ProgressRing';
import { Button } from './Button';
import { useJudgeGuide, GUIDE_STEPS, recordGuideStep } from '../../context/JudgeGuideContext';

export { recordGuideStep };

export const JudgeGuide: React.FC = () => {
  const navigate = useNavigate();
  const {
    isOpen,
    closeGuide,
    completedSteps,
    totalSteps,
    completedCount,
    progressPercent,
    isEnabled,
  } = useJudgeGuide();

  // Close sheet on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        closeGuide();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, closeGuide]);

  if (!isEnabled || !isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-modal overflow-hidden"
      role="dialog"
      aria-modal="true"
      aria-label="Judge Quick-Start Guide"
    >
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-slate-950/60 backdrop-blur-sm transition-opacity"
        onClick={closeGuide}
        aria-hidden="true"
      />

      {/* Popover / Sheet: full-screen on mobile (< 768px), 420px slide-over on >= 768px */}
      <div className="fixed inset-y-0 right-0 max-w-full flex">
        <div
          className="w-screen md:w-[420px] max-w-full bg-surface text-text-main shadow-2xl flex flex-col border-l border-border h-full"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="p-4 sm:p-5 border-b border-border bg-slate-50/80 dark:bg-slate-900/50 flex items-center justify-between flex-shrink-0">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-navy/10 dark:bg-teal/20 flex items-center justify-center text-navy dark:text-teal">
                <Compass className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-text-main">Quick-Start Guide</h3>
                <p className="text-[11px] text-text-muted">Interactive verification journey</p>
              </div>
            </div>
            <button
              onClick={closeGuide}
              className="p-2 min-w-[40px] min-h-[40px] flex items-center justify-center text-text-muted hover:text-text-main rounded-btn hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              title="Close guide"
              aria-label="Close guide"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Progress Summary */}
          <div className="p-4 bg-navy/5 dark:bg-slate-800/40 border-b border-border flex items-center justify-between gap-4 flex-shrink-0">
            <div>
              <h4 className="text-xs font-semibold text-text-main">Hackathon Workflow Progress</h4>
              <p className="text-[11px] text-text-muted mt-0.5">
                {completedCount} of {totalSteps} core capabilities explored
              </p>
            </div>
            <ProgressRing progress={progressPercent} size={48} strokeWidth={5} color="#0F766E" showPercent />
          </div>

          {/* Steps Checklist */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {GUIDE_STEPS.map((step) => {
              const isDone = completedSteps.includes(step.id);
              return (
                <div
                  key={step.id}
                  className={`p-3.5 rounded-card border transition-all ${
                    isDone
                      ? 'bg-emerald-50/40 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-800/50'
                      : 'bg-surface border-border hover:border-slate-300 dark:hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5 flex-shrink-0">
                      {isDone ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                      ) : (
                        <Circle className="w-4 h-4 text-text-muted" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <h4
                        className={`text-xs font-semibold ${
                          isDone
                            ? 'text-emerald-900 dark:text-emerald-200 line-through'
                            : 'text-text-main'
                        }`}
                      >
                        {step.title}
                      </h4>
                      <p className="text-[11px] text-text-muted mt-1 leading-relaxed">
                        {step.description}
                      </p>
                      <div className="mt-2.5 flex items-center justify-between">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-[11px] h-7 px-2"
                          rightIcon={<ChevronRight className="w-3 h-3" />}
                          onClick={() => {
                            closeGuide();
                            navigate(step.actionUrl);
                          }}
                        >
                          {step.actionLabel}
                        </Button>
                        {isDone && (
                          <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider">
                            Verified
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Footer note */}
          <div className="p-3 bg-slate-50 dark:bg-slate-900 border-t border-border text-center text-[11px] text-text-muted flex-shrink-0">
            Checklist auto-updates as you use features in real time.
          </div>
        </div>
      </div>
    </div>
  );
};
