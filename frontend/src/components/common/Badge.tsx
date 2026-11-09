import React from 'react';
import {
  CheckCircle,
  HelpCircle,
  AlertTriangle,
  Sparkles,
  UserCheck,
  Lock,
  GitBranch,
  ShieldAlert,
  Calendar,
  Layers,
  Phone,
  User,
  Activity,
  ArrowRight,
} from 'lucide-react';
import { ClaimStatus, ClaimType } from '../../types';

interface StatusBadgeProps {
  status: ClaimStatus;
  isLeaverAttested?: boolean;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  isLeaverAttested = false,
  size = 'md',
}) => {
  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs font-medium';

  if (isLeaverAttested) {
    return (
      <span
        className={`inline-flex items-center gap-1.5 rounded-full bg-status-leaver-bg text-status-leaver-text border border-status-leaver-border ${sizeClasses}`}
      >
        <UserCheck className="w-3.5 h-3.5 flex-shrink-0" />
        <span>Leaver-attested</span>
      </span>
    );
  }

  switch (status) {
    case 'verified':
      return (
        <span
          className={`inline-flex items-center gap-1.5 rounded-full bg-status-verified-bg text-status-verified-text border border-status-verified-border font-medium ${sizeClasses}`}
        >
          <CheckCircle className="w-3.5 h-3.5 flex-shrink-0" />
          <span>Verified</span>
        </span>
      );
    case 'inferred':
      return (
        <span
          className={`inline-flex items-center gap-1.5 rounded-full bg-status-inferred-bg text-status-inferred-text border border-status-inferred-border font-medium ${sizeClasses}`}
        >
          <Sparkles className="w-3.5 h-3.5 flex-shrink-0" />
          <span>Inferred</span>
        </span>
      );
    case 'conflicting':
      return (
        <span
          className={`inline-flex items-center gap-1.5 rounded-full bg-status-conflicting-bg text-status-conflicting-text border border-status-conflicting-border font-semibold ${sizeClasses}`}
        >
          <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
          <span>Conflicting</span>
        </span>
      );
    case 'missing':
      return (
        <span
          className={`inline-flex items-center gap-1.5 rounded-full bg-status-missing-bg text-status-missing-text border border-status-missing-border font-medium ${sizeClasses}`}
        >
          <HelpCircle className="w-3.5 h-3.5 flex-shrink-0" />
          <span>Missing</span>
        </span>
      );
    case 'restricted':
      return (
        <span
          className={`inline-flex items-center gap-1.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 border border-border font-medium ${sizeClasses}`}
        >
          <Lock className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
          <span>Restricted</span>
        </span>
      );
    default:
      return null;
  }
};

interface ClearanceBadgeProps {
  clearance: number;
  size?: 'sm' | 'md';
}

export const ClearanceBadge: React.FC<ClearanceBadgeProps> = ({ clearance, size = 'md' }) => {
  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs font-medium';

  if (clearance === 1) {
    return (
      <span
        className={`inline-flex items-center gap-1.5 rounded-md bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 ${sizeClasses}`}
        title="Clearance Level 1: General (Visible to all team roles)"
      >
        <span className="w-2 h-2 rounded-full bg-emerald-500" />
        <span>General</span>
      </span>
    );
  } else if (clearance === 2) {
    return (
      <span
        className={`inline-flex items-center gap-1.5 rounded-md bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800 ${sizeClasses}`}
        title="Clearance Level 2: Technical (Visible to Developers and Lead)"
      >
        <span className="w-2 h-2 rounded-full bg-blue-500" />
        <span>Technical</span>
      </span>
    );
  } else {
    return (
      <span
        className={`inline-flex items-center gap-1.5 rounded-md bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800 ${sizeClasses}`}
        title="Clearance Level 3: Confidential (Project Lead only)"
      >
        <Lock className="w-3 h-3 text-rose-600 flex-shrink-0" />
        <span>Confidential</span>
      </span>
    );
  }
};

export const ClaimTypeBadge: React.FC<{ type: ClaimType; size?: 'sm' | 'md' }> = ({
  type,
  size = 'md',
}) => {
  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2 py-0.5 text-xs font-medium';

  const typeConfig: Record<string, { label: string; icon: React.ReactNode; bg: string; text: string }> = {
    decision: { label: 'Decision', icon: <GitBranch className="w-3 h-3" />, bg: 'bg-indigo-50 dark:bg-indigo-950/40 border-indigo-200 dark:border-indigo-800', text: 'text-indigo-700 dark:text-indigo-300' },
    open_work: { label: 'Open Work', icon: <Activity className="w-3 h-3" />, bg: 'bg-cyan-50 dark:bg-cyan-950/40 border-cyan-200 dark:border-cyan-800', text: 'text-cyan-700 dark:text-cyan-300' },
    owner: { label: 'Owner', icon: <User className="w-3 h-3" />, bg: 'bg-teal-50 dark:bg-teal-950/40 border-teal-200 dark:border-teal-800', text: 'text-teal-700 dark:text-teal-300' },
    risk: { label: 'Risk', icon: <ShieldAlert className="w-3 h-3" />, bg: 'bg-amber-50 dark:bg-amber-950/40 border-amber-200 dark:border-amber-800', text: 'text-amber-800 dark:text-amber-300' },
    dependency: { label: 'Dependency', icon: <Layers className="w-3 h-3" />, bg: 'bg-purple-50 dark:bg-purple-950/40 border-purple-200 dark:border-purple-800', text: 'text-purple-700 dark:text-purple-300' },
    contact: { label: 'Contact', icon: <Phone className="w-3 h-3" />, bg: 'bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-800', text: 'text-emerald-700 dark:text-emerald-300' },
    recurring_problem: { label: 'Recurring Issue', icon: <AlertTriangle className="w-3 h-3" />, bg: 'bg-orange-50 dark:bg-orange-950/40 border-orange-200 dark:border-orange-800', text: 'text-orange-700 dark:text-orange-300' },
    next_action: { label: 'Next Action', icon: <ArrowRight className="w-3 h-3" />, bg: 'bg-sky-50 dark:bg-sky-950/40 border-sky-200 dark:border-sky-800', text: 'text-sky-700 dark:text-sky-300' },
    change: { label: 'Change', icon: <Calendar className="w-3 h-3" />, bg: 'bg-blue-50 dark:bg-blue-950/40 border-blue-200 dark:border-blue-800', text: 'text-blue-700 dark:text-blue-300' },
    restricted: { label: 'Restricted', icon: <Lock className="w-3 h-3" />, bg: 'bg-slate-100 dark:bg-slate-800 border-border', text: 'text-slate-500 dark:text-slate-400' },
  };

  const item = typeConfig[type] || { label: type, icon: null, bg: 'bg-slate-50 dark:bg-slate-800 border-border', text: 'text-text-main' };

  return (
    <span className={`inline-flex items-center gap-1 rounded border ${item.bg} ${item.text} ${sizeClasses}`}>
      {item.icon}
      <span>{item.label}</span>
    </span>
  );
};
