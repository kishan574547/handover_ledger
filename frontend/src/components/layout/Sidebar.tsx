import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Database,
  FileSpreadsheet,
  Clock,
  HelpCircle,
  CheckSquare,
  ShieldCheck,
  ListChecks,
  HelpCircle as InfoIcon,
  ShieldAlert,
} from 'lucide-react';
import { useRole } from '../../context/RoleContext';

export const Sidebar: React.FC = () => {
  const { role } = useRole();

  // Navigation filtering according to spec:
  // - developer & coordinator: Dashboard, Handover, How it works
  // - departing: Dashboard, Claim Ledger, Timeline, Exit Interview, Handover, How it works
  // - lead: all pages
  const navItems = [
    {
      to: '/',
      label: 'Dashboard',
      icon: <LayoutDashboard className="w-4 h-4" />,
      allowedRoles: ['lead', 'departing', 'developer', 'coordinator'],
    },
    {
      to: '/sources',
      label: 'Sources',
      icon: <Database className="w-4 h-4" />,
      allowedRoles: ['lead'],
    },
    {
      to: '/ledger',
      label: 'Claim Ledger',
      icon: <FileSpreadsheet className="w-4 h-4" />,
      allowedRoles: ['lead', 'departing'],
    },
    {
      to: '/timeline',
      label: 'Timeline',
      icon: <Clock className="w-4 h-4" />,
      allowedRoles: ['lead', 'departing'],
    },
    {
      to: '/interview',
      label: 'Exit Interview',
      icon: <HelpCircle className="w-4 h-4" />,
      allowedRoles: ['lead', 'departing'],
    },
    {
      to: '/review',
      label: 'Review & Approve',
      icon: <CheckSquare className="w-4 h-4" />,
      allowedRoles: ['lead'],
    },
    {
      to: '/handover',
      label: 'Handover View',
      icon: <ShieldCheck className="w-4 h-4" />,
      allowedRoles: ['lead', 'departing', 'developer', 'coordinator'],
    },
    {
      to: '/activity',
      label: 'Activity Log',
      icon: <ListChecks className="w-4 h-4" />,
      allowedRoles: ['lead'],
    },
    {
      to: '/how-it-works',
      label: 'How It Works',
      icon: <InfoIcon className="w-4 h-4" />,
      allowedRoles: ['lead', 'departing', 'developer', 'coordinator'],
    },
  ];

  const visibleNav = navItems.filter((item) => item.allowedRoles.includes(role));

  return (
    <aside className="w-60 bg-navy text-white flex flex-col flex-shrink-0 min-h-screen select-none border-r border-navy-dark shadow-md z-30">
      {/* Brand Header */}
      <div className="h-16 px-5 flex items-center gap-3 border-b border-navy-light/40">
        <div className="w-8 h-8 rounded-lg bg-teal flex items-center justify-center text-white shadow-sm">
          <ShieldAlert className="w-5 h-5" />
        </div>
        <div>
          <h1 className="font-bold text-base tracking-tight leading-none text-white">HandoverLedger</h1>
          <p className="text-[10px] text-slate-300 mt-1 uppercase font-semibold tracking-wider">Verifiable Handover</p>
        </div>
      </div>

      {/* Nav List */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {visibleNav.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                isActive
                  ? 'bg-navy-light text-white shadow-sm'
                  : 'text-slate-300 hover:bg-navy-light/50 hover:text-white'
              }`
            }
          >
            <span className="flex-shrink-0 text-slate-300">{item.icon}</span>
            <span className="truncate">{item.label}</span>
          </NavLink>
        ))}
      </nav>

      {/* Trust Rules footnote */}
      <div className="p-4 border-t border-navy-light/40 bg-navy-dark/40 text-[11px] text-slate-400 space-y-1">
        <p className="font-semibold text-slate-300">Strict Clearance Model</p>
        <p className="text-[10px] leading-tight text-slate-400">
          Claims strictly filtered at DB layer. Confidential data never leaks to lower roles.
        </p>
      </div>
    </aside>
  );
};

