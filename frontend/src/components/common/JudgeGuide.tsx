import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Compass,
  CheckCircle2,
  Circle,
  X,
  ChevronRight,
  Sparkles,
  HelpCircle,
  ExternalLink,
} from 'lucide-react';
import { ProgressRing } from './ProgressRing';
import { Button } from './Button';
import { useRole } from '../../context/RoleContext';

export interface GuideStep {
  id: string;
  title: string;
  description: string;
  actionUrl: string;
  actionLabel: string;
}

const GUIDE_STEPS: GuideStep[] = [
  {
    id: 'load_demo',
    title: '1. Load Demo Project',
    description: 'Populate the verified "Campus Connect" synthetic repository and notes.',
    actionUrl: '/',
    actionLabel: 'Go to Dashboard',
  },
  {
    id: 'run_analysis',
    title: '2. Run AI Analysis',
    description: 'Trigger the 6-stage extraction, verification, conflict, and gap detection pipeline.',
    actionUrl: '/sources',
    actionLabel: 'View Sources & Analysis',
  },
  {
    id: 'open_evidence',
    title: '3. Inspect Verbatim Citations',
    description: 'Open the evidence drawer on any claim to inspect exact verbatim quotes and fuzzy match scores.',
    actionUrl: '/ledger',
    actionLabel: 'Open Claim Ledger',
  },
  {
    id: 'resolve_conflict',
    title: '4. Resolve a Disputed Fact',
    description: 'Compare contradictory claims side-by-side and commit a resolution.',
    actionUrl: '/ledger',
    actionLabel: 'Resolve in Ledger',
  },
  {
    id: 'answer_question',
    title: '5. Complete Exit Interview',
    description: 'Attest leaver knowledge for automatically identified knowledge gaps.',
    actionUrl: '/interview',
    actionLabel: 'Answer Questions',
  },
  {
    id: 'approve_handover',
    title: '6. Review & Approve Handover',
    description: 'Verify the release checklist, save a version snapshot, and approve the release.',
    actionUrl: '/review',
    actionLabel: 'Review & Approve',
  },
  {
    id: 'switch_role',
    title: '7. Test Clearance Isolation',
    description: 'Switch to Developer or Coordinator in topbar and verify that Level 3 secrets are completely blocked.',
    actionUrl: '/handover',
    actionLabel: 'View as Other Role',
  },
  {
    id: 'ask_handover',
    title: '8. Ask Grounded Q&A',
    description: 'Query Ask the Handover to see answers strictly cited from verified evidence.',
    actionUrl: '/ask',
    actionLabel: 'Ask the Handover',
  },
];

export const JudgeGuide: React.FC = () => {
  const navigate = useNavigate();
  const { role } = useRole();

  const [isOpen, setIsOpen] = useState(false);
  const [completedSteps, setCompletedSteps] = useState<string[]>(() => {
    try {
      const saved = localStorage.getItem('handover_completed_guide_steps');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  const [showPrompt, setShowPrompt] = useState<boolean>(() => {
    return localStorage.getItem('handover_guide_prompt_dismissed') !== 'true';
  });

  const [isEnabled, setIsEnabled] = useState<boolean>(() => {
    return localStorage.getItem('handover_show_judge_guide') !== 'false';
  });

  // Listen to preference changes or custom step completion events
  useEffect(() => {
    const handleStepEvent = (e: any) => {
      if (e.detail && e.detail.stepId) {
        setCompletedSteps((prev) => {
          if (!prev.includes(e.detail.stepId)) {
            const next = [...prev, e.detail.stepId];
            localStorage.setItem('handover_completed_guide_steps', JSON.stringify(next));
            return next;
          }
          return prev;
        });
      }
    };

    const handlePrefChange = () => {
      setIsEnabled(localStorage.getItem('handover_show_judge_guide') !== 'false');
    };

    window.addEventListener('handover_guide_step_done', handleStepEvent);
    window.addEventListener('judge_guide_pref_changed', handlePrefChange);
    return () => {
      window.removeEventListener('handover_guide_step_done', handleStepEvent);
      window.removeEventListener('judge_guide_pref_changed', handlePrefChange);
    };
  }, []);

  if (!isEnabled) return null;

  const totalSteps = GUIDE_STEPS.length;
  const progressPercent = Math.round((completedSteps.length / totalSteps) * 100);

  const dismissPrompt = () => {
    setShowPrompt(false);
    localStorage.setItem('handover_guide_prompt_dismissed', 'true');
  };

  return (
    <>
      {/* 1. Floating Quick-Start Trigger Button */}
      <div className="fixed bottom-20 md:bottom-6 right-4 sm:right-6 z-40 flex items-center gap-2 judge-guide-panel">
        {showPrompt && !isOpen && (
          <div className="hidden sm:flex items-center gap-2 p-2 px-3 rounded-card bg-surface border border-border shadow-card text-xs text-text-main animate-bounce">
            <Sparkles className="w-4 h-4 text-amber-500" />
            <span>Judge Guide: interactive tour</span>
            <button onClick={dismissPrompt} className="text-text-muted hover:text-text-main p-0.5 ml-1">
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        <button
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center gap-2 px-3.5 py-2.5 rounded-full bg-navy text-white hover:bg-navy-hover dark:bg-teal dark:text-slate-950 shadow-card font-medium text-xs transition-all min-h-[44px] focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-navy"
          aria-label="Open Judge Quick-Start Guide"
        >
          <Compass className="w-4 h-4 animate-spin-slow" />
          <span className="font-semibold">Quick Start</span>
          <span className="px-1.5 py-0.5 rounded-full bg-white/20 text-[10px] font-bold">
            {completedSteps.length}/{totalSteps}
          </span>
        </button>
      </div>

      {/* 2. Slide-over Checklist Panel */}
      {isOpen && (
        <div className="fixed inset-0 z-50 overflow-hidden" role="dialog" aria-modal="true">
          <div
            className="fixed inset-0 bg-slate-950/60 backdrop-blur-sm transition-opacity"
            onClick={() => setIsOpen(false)}
          />

          <div className="fixed inset-y-0 right-0 max-w-full flex">
            <div
              className="w-screen sm:w-[420px] max-w-full bg-surface text-text-main shadow-2xl flex flex-col border-l border-border h-full"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Header */}
              <div className="p-5 border-b border-border bg-slate-50/80 dark:bg-slate-900/50 flex items-center justify-between flex-shrink-0">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-navy/10 dark:bg-teal/20 flex items-center justify-center text-navy dark:text-teal">
                    <Compass className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-text-main">Judge Quick-Start Guide</h3>
                    <p className="text-[11px] text-text-muted">Interactive verification journey</p>
                  </div>
                </div>
                <button
                  onClick={() => setIsOpen(false)}
                  className="p-2 min-w-[40px] min-h-[40px] flex items-center justify-center text-text-muted hover:text-text-main rounded-btn"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Progress Summary */}
              <div className="p-4 bg-navy/5 dark:bg-slate-800/40 border-b border-border flex items-center justify-between gap-4 flex-shrink-0">
                <div>
                  <h4 className="text-xs font-semibold text-text-main">Hackathon Workflow Progress</h4>
                  <p className="text-[11px] text-text-muted mt-0.5">
                    {completedSteps.length} of {totalSteps} core capabilities explored
                  </p>
                </div>
                <ProgressRing progress={progressPercent} size={48} strokeWidth={5} color="#0F766E" />
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
                          <h4 className={`text-xs font-semibold ${isDone ? 'text-emerald-900 dark:text-emerald-200 line-through' : 'text-text-main'}`}>
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
                                setIsOpen(false);
                                navigate(step.actionUrl);
                              }}
                            >
                              {step.actionLabel}
                            </Button>
                            {!isDone && (
                              <button
                                onClick={() => {
                                  const next = [...completedSteps, step.id];
                                  setCompletedSteps(next);
                                  localStorage.setItem('handover_completed_guide_steps', JSON.stringify(next));
                                }}
                                className="text-[10px] text-text-muted hover:text-text-main underline"
                              >
                                Mark done
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Footer */}
              <div className="p-3.5 border-t border-border bg-slate-50 dark:bg-slate-900/40 flex items-center justify-between text-xs text-text-muted flex-shrink-0">
                <button
                  onClick={() => {
                    setCompletedSteps([]);
                    localStorage.removeItem('handover_completed_guide_steps');
                  }}
                  className="text-[11px] text-text-muted hover:text-rose-600 transition-colors"
                >
                  Reset Progress
                </button>
                <Button variant="primary" size="sm" onClick={() => setIsOpen(false)}>
                  Done
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

/** Helper to dispatch step completion from anywhere in the app */
export function recordGuideStep(stepId: string) {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('handover_guide_step_done', { detail: { stepId } }));
  }
}

