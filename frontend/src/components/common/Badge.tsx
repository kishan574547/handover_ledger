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
        <UserCheck className="w-3.5 h-3.5" />
        <span>Leaver-attested</span>
      </span>
    );
  }

  switch (status) {
    case 'verified':
      return (
        <span
          className={`inline-flex items-center gap-1.5 rounded-full bg-status-verified-bg text-status-verified-text border border-status-verified-border ${sizeClasses}`}
        >
          <CheckCircle className="w-3.5 h-3.5" />
          <span>Verified</span>
        </span>
      );
    case 'inferred':
      return (
        <span
          className={`inline-flex items-center gap-1.5 rounded-full bg-status-inferred-bg text-status-inferred-text border border-status-inferred-border ${sizeClasses}`}
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span>Inferred</span>
        </span>
      );
    case 'conflicting':
      return (
        <span
          className={`inline-flex items-center gap-1.5 rounded-full bg-status-conflicting-bg text-status-conflicting-text border border-status-conflicting-border font-semibold ${sizeClasses}`}
        >
          <AlertTriangle className="w-3.5 h-3.5" />
          <span>Conflicting</span>
        </span>
      );
    case 'missing':
      return (
        <span
          className={`inline-flex items-center gap-1.5 rounded-full bg-status-missing-bg text-status-missing-text border border-status-missing-border ${sizeClasses}`}
        >
          <HelpCircle className="w-3.5 h-3.5" />
          <span>Missing</span>
        </span>
      );
    case 'restricted':
      return (
        <span
          className={`inline-flex items-center gap-1.5 rounded-full bg-slate-100 text-slate-500 border border-slate-200 ${sizeClasses}`}
        >
          <Lock className="w-3.5 h-3.5 text-slate-400" />
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
        className={`inline-flex items-center gap-1.5 rounded-md bg-emerald-50 text-emerald-700 border border-emerald-200 ${sizeClasses}`}
        title="Clearance Level 1: General (Visible to all team roles)"
      >
        <span className="w-2 h-2 rounded-full bg-emerald-500" />
        <span>General</span>
      </span>
    );
  } else if (clearance === 2) {
    return (
      <span
        className={`inline-flex items-center gap-1.5 rounded-md bg-blue-50 text-blue-700 border border-blue-200 ${sizeClasses}`}
        title="Clearance Level 2: Technical (Visible to Developers and Lead)"
      >
        <span className="w-2 h-2 rounded-full bg-blue-500" />
        <span>Technical</span>
      </span>
    );
  } else {
    return (
      <span
        className={`inline-flex items-center gap-1.5 rounded-md bg-rose-50 text-rose-700 border border-rose-200 ${sizeClasses}`}
        title="Clearance Level 3: Confidential (Project Lead only)"
      >
        <Lock className="w-3 h-3 text-rose-600" />
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
    decision: { label: 'Decision', icon: <GitBranch className="w-3 h-3" />, bg: 'bg-indigo-50 border-indigo-200', text: 'text-indigo-700' },
    open_work: { label: 'Open Work', icon: <Activity className="w-3 h-3" />, bg: 'bg-cyan-50 border-cyan-200', text: 'text-cyan-700' },
    owner: { label: 'Owner', icon: <User className="w-3 h-3" />, bg: 'bg-teal-50 border-teal-200', text: 'text-teal-700' },
    risk: { label: 'Risk', icon: <ShieldAlert className="w-3 h-3" />, bg: 'bg-amber-50 border-amber-200', text: 'text-amber-800' },
    dependency: { label: 'Dependency', icon: <Layers className="w-3 h-3" />, bg: 'bg-purple-50 border-purple-200', text: 'text-purple-700' },
    contact: { label: 'Contact', icon: <Phone className="w-3 h-3" />, bg: 'bg-emerald-50 border-emerald-200', text: 'text-emerald-700' },
    recurring_problem: { label: 'Recurring Issue', icon: <AlertTriangle className="w-3 h-3" />, bg: 'bg-orange-50 border-orange-200', text: 'text-orange-700' },
    next_action: { label: 'Next Action', icon: <ArrowRight className="w-3 h-3" />, bg: 'bg-sky-50 border-sky-200', text: 'text-sky-700' },
    change: { label: 'Change', icon: <Calendar className="w-3 h-3" />, bg: 'bg-blue-50 border-blue-200', text: 'text-blue-700' },
    restricted: { label: 'Restricted', icon: <Lock className="w-3 h-3" />, bg: 'bg-slate-100 border-slate-200', text: 'text-slate-500' },
  };

  const item = typeConfig[type] || { label: type, icon: null, bg: 'bg-slate-50 border-slate-200', text: 'text-slate-700' };

  return (
    <span className={`inline-flex items-center gap-1 rounded border ${item.bg} ${item.text} ${sizeClasses}`}>
      {item.icon}
      <span>{item.label}</span>
    </span>
  );
};

