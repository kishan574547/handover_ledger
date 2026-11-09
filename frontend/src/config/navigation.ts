import React from 'react';
import {
  LayoutDashboard,
  Database,
  FileSpreadsheet,
  Clock,
  HelpCircle,
  CheckSquare,
  ShieldCheck,
  MessageSquareQuote,
  ListChecks,
  BookOpen,
  Settings,
} from 'lucide-react';
import { DemoRole } from '../types';

export interface NavItemConfig {
  id: string;
  to: string;
  label: string;
  shortLabel?: string;
  icon: React.ComponentType<{ className?: string }>;
  allowedRoles: DemoRole[];
  group: 'workspace' | 'handover' | 'system';
  badgeKey?: 'pendingClaims' | 'openConflicts' | 'openQuestions';
}

export const ALL_NAV_ITEMS: NavItemConfig[] = [
  // Workspace group
  {
    id: 'dashboard',
    to: '/',
    label: 'Dashboard',
    shortLabel: 'Overview',
    icon: LayoutDashboard,
    allowedRoles: ['lead', 'departing', 'developer', 'coordinator'],
    group: 'workspace',
  },
  {
    id: 'sources',
    to: '/sources',
    label: 'Sources',
    shortLabel: 'Sources',
    icon: Database,
    allowedRoles: ['lead'],
    group: 'workspace',
  },
  {
    id: 'ledger',
    to: '/ledger',
    label: 'Claim Ledger',
    shortLabel: 'Ledger',
    icon: FileSpreadsheet,
    allowedRoles: ['lead', 'departing'],
    group: 'workspace',
    badgeKey: 'pendingClaims',
  },
  {
    id: 'timeline',
    to: '/timeline',
    label: 'Timeline',
    shortLabel: 'Timeline',
    icon: Clock,
    allowedRoles: ['lead', 'departing'],
    group: 'workspace',
  },
  {
    id: 'interview',
    to: '/interview',
    label: 'Exit Interview',
    shortLabel: 'Interview',
    icon: HelpCircle,
    allowedRoles: ['lead', 'departing'],
    group: 'workspace',
    badgeKey: 'openQuestions',
  },

  // Handover group
  {
    id: 'review',
    to: '/review',
    label: 'Review & Approve',
    shortLabel: 'Review',
    icon: CheckSquare,
    allowedRoles: ['lead'],
    group: 'handover',
    badgeKey: 'openConflicts',
  },
  {
    id: 'handover',
    to: '/handover',
    label: 'Handover View',
    shortLabel: 'Handover',
    icon: ShieldCheck,
    allowedRoles: ['lead', 'departing', 'developer', 'coordinator'],
    group: 'handover',
  },
  {
    id: 'ask',
    to: '/ask',
    label: 'Ask the Handover',
    shortLabel: 'Ask Q&A',
    icon: MessageSquareQuote,
    allowedRoles: ['lead', 'departing', 'developer', 'coordinator'],
    group: 'handover',
  },

  // System group
  {
    id: 'activity',
    to: '/activity',
    label: 'Activity Log',
    shortLabel: 'Activity',
    icon: ListChecks,
    allowedRoles: ['lead'],
    group: 'system',
  },
  {
    id: 'how-it-works',
    to: '/how-it-works',
    label: 'How It Works',
    shortLabel: 'Guide',
    icon: BookOpen,
    allowedRoles: ['lead', 'departing', 'developer', 'coordinator'],
    group: 'system',
  },
  {
    id: 'settings',
    to: '/settings',
    label: 'Settings',
    shortLabel: 'Settings',
    icon: Settings,
    allowedRoles: ['lead', 'departing', 'developer', 'coordinator'],
    group: 'system',
  },
];

export const NAV_GROUPS = [
  { id: 'workspace', label: 'Workspace' },
  { id: 'handover', label: 'Handover' },
  { id: 'system', label: 'System' },
] as const;

/**
 * Returns the 4 primary navigation items for phones per role
 */
export function getPhoneBottomNavItems(role: DemoRole): NavItemConfig[] {
  switch (role) {
    case 'lead':
      return [
        ALL_NAV_ITEMS.find((n) => n.id === 'dashboard')!,
        ALL_NAV_ITEMS.find((n) => n.id === 'ledger')!,
        ALL_NAV_ITEMS.find((n) => n.id === 'review')!,
        ALL_NAV_ITEMS.find((n) => n.id === 'handover')!,
      ];
    case 'departing':
      return [
        ALL_NAV_ITEMS.find((n) => n.id === 'dashboard')!,
        ALL_NAV_ITEMS.find((n) => n.id === 'interview')!,
        ALL_NAV_ITEMS.find((n) => n.id === 'ledger')!,
        ALL_NAV_ITEMS.find((n) => n.id === 'handover')!,
      ];
    case 'developer':
    case 'coordinator':
    default:
      return [
        ALL_NAV_ITEMS.find((n) => n.id === 'dashboard')!,
        ALL_NAV_ITEMS.find((n) => n.id === 'handover')!,
        ALL_NAV_ITEMS.find((n) => n.id === 'ask')!,
        ALL_NAV_ITEMS.find((n) => n.id === 'how-it-works')!,
      ];
  }
}

