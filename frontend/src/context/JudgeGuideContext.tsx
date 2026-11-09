import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

export interface GuideStep {
  id: string;
  title: string;
  description: string;
  actionUrl: string;
  actionLabel: string;
}

export const GUIDE_STEPS: GuideStep[] = [
  {
    id: 'load_demo',
    title: '1. Load Demo Project',
    description: 'Populate verified synthetic repository sources and notes for evaluation.',
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

export function recordGuideStep(stepId: string) {
  try {
    const saved = localStorage.getItem('handover_completed_guide_steps');
    const existing: string[] = saved ? JSON.parse(saved) : [];
    if (!existing.includes(stepId)) {
      const updated = [...existing, stepId];
      localStorage.setItem('handover_completed_guide_steps', JSON.stringify(updated));
    }
  } catch {}
  window.dispatchEvent(new CustomEvent('handover_guide_step_done', { detail: { stepId } }));
}

interface JudgeGuideContextType {
  isOpen: boolean;
  openGuide: () => void;
  closeGuide: () => void;
  toggleGuide: () => void;
  completedSteps: string[];
  totalSteps: number;
  completedCount: number;
  progressPercent: number;
  recordStep: (stepId: string) => void;
  isEnabled: boolean;
}

const JudgeGuideContext = createContext<JudgeGuideContextType | undefined>(undefined);

export const JudgeGuideProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [completedSteps, setCompletedSteps] = useState<string[]>(() => {
    try {
      const saved = localStorage.getItem('handover_completed_guide_steps');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  const [isEnabled, setIsEnabled] = useState<boolean>(() => {
    return localStorage.getItem('handover_show_judge_guide') !== 'false';
  });

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

    const handleOpenEvent = () => {
      setIsOpen(true);
    };

    const handlePrefChange = () => {
      setIsEnabled(localStorage.getItem('handover_show_judge_guide') !== 'false');
    };

    window.addEventListener('handover_guide_step_done', handleStepEvent);
    window.addEventListener('open_judge_guide', handleOpenEvent);
    window.addEventListener('judge_guide_pref_changed', handlePrefChange);

    return () => {
      window.removeEventListener('handover_guide_step_done', handleStepEvent);
      window.removeEventListener('open_judge_guide', handleOpenEvent);
      window.removeEventListener('judge_guide_pref_changed', handlePrefChange);
    };
  }, []);

  const totalSteps = GUIDE_STEPS.length;
  const completedCount = completedSteps.length;
  const progressPercent = Math.round((completedCount / totalSteps) * 100);

  const openGuide = () => setIsOpen(true);
  const closeGuide = () => setIsOpen(false);
  const toggleGuide = () => setIsOpen((prev) => !prev);

  return (
    <JudgeGuideContext.Provider
      value={{
        isOpen,
        openGuide,
        closeGuide,
        toggleGuide,
        completedSteps,
        totalSteps,
        completedCount,
        progressPercent,
        recordStep: recordGuideStep,
        isEnabled,
      }}
    >
      {children}
    </JudgeGuideContext.Provider>
  );
};

export const useJudgeGuide = () => {
  const ctx = useContext(JudgeGuideContext);
  if (!ctx) {
    throw new Error('useJudgeGuide must be used within a JudgeGuideProvider');
  }
  return ctx;
};

