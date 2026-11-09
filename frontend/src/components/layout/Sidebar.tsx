import React, { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  ChevronLeft,
  ChevronRight,
  Lock,
  X,
  Shield,
  Layers,
  Compass,
} from 'lucide-react';
import { useRole } from '../../context/RoleContext';
import { useJudgeGuide } from '../../context/JudgeGuideContext';
import { useProjectMeta } from '../../context/ProjectMetaContext';
import { ALL_NAV_ITEMS, NAV_GROUPS, NavItemConfig } from '../../config/navigation';
import { api } from '../../api/client';
import { ClearanceBadge } from '../common/Badge';

interface SidebarProps {
  isMobileDrawerOpen?: boolean;
  onCloseMobileDrawer?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isMobileDrawerOpen = false,
  onCloseMobileDrawer,
}) => {
  const { role, roleConfig } = useRole();
  const { openGuide, completedCount, totalSteps } = useJudgeGuide();
  const { isDemo, isOwn, isEmpty } = useProjectMeta();

  // Collapsed state persisted in localStorage (affects screens >= 1024px)
  const [isCollapsed, setIsCollapsed] = useState<boolean>(() => {
    return localStorage.getItem('handover_sidebar_collapsed') === 'true';
  });

  const toggleCollapse = () => {
    setIsCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem('handover_sidebar_collapsed', String(next));
      return next;
    });
  };

  // Close mobile drawer on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isMobileDrawerOpen && onCloseMobileDrawer) {
        onCloseMobileDrawer();
      }
    };
    if (isMobileDrawerOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isMobileDrawerOpen, onCloseMobileDrawer]);

  // Fetch live count badges from dashboard and claims
  const { data: dashboardData } = useQuery({
    queryKey: ['dashboard'],
    queryFn: api.getDashboard,
    staleTime: 10000,
  });

  const { data: claimsData } = useQuery({
    queryKey: ['claims', 'pending_count'],
    queryFn: () => api.getClaims({ limit: 100 }),
    staleTime: 15000,
    enabled: role === 'lead' || role === 'departing',
  });

  // Calculate live badge counts
  const badgeCounts: Record<string, number> = {
    pendingClaims: claimsData?.claims
      ? claimsData.claims.filter((c: any) => c.review_state === 'pending').length
      : 0,
    openConflicts: dashboardData?.open_conflicts_count ?? 0,
    openQuestions: dashboardData?.unanswered_questions_count ?? 0,
  };

  // Filter navigation items for the current role
  const visibleNavItems = ALL_NAV_ITEMS.filter((item) => item.allowedRoles.includes(role));

  const renderNavList = (isRail: boolean) => (
    <div className="flex-1 overflow-y-auto px-2.5 py-3 space-y-4">
      {NAV_GROUPS.map((group) => {
        const groupItems = visibleNavItems.filter((item) => item.group === group.id);
        if (groupItems.length === 0) return null;

        return (
          <div key={group.id} className="space-y-1">
            {!isRail && (
              <h3 className="px-3 text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-400 select-none mb-1">
                {group.label}
              </h3>
            )}
            {groupItems.map((item) => {
              const Icon = item.icon;
              const count = item.badgeKey ? badgeCounts[item.badgeKey] || 0 : 0;

              return (
                <NavLink
                  key={item.id}
                  to={item.to}
                  end={item.to === '/'}
                  onClick={() => {
                    if (onCloseMobileDrawer) onCloseMobileDrawer();
                  }}
                  title={isRail ? `${item.label} ${count > 0 ? `(${count})` : ''}` : undefined}
                  className={({ isActive }) =>
                    `group relative flex items-center gap-3 px-3 py-2.5 rounded-btn text-xs sm:text-sm font-medium transition-all min-h-[44px] ${
                      isRail ? 'justify-center px-2' : ''
                    } ${
                      isActive
                        ? 'bg-navy-light text-white shadow-sm dark:bg-slate-800 dark:text-teal font-semibold'
                        : 'text-slate-300 hover:bg-navy-light/40 hover:text-white dark:hover:bg-slate-800/50'
                    }`
                  }
                >
                  <Icon className="w-4 h-4 flex-shrink-0 text-slate-300 group-hover:text-white" />
                  {!isRail && <span className="truncate flex-1">{item.label}</span>}
                  {!isRail && count > 0 && (
                    <span className="flex-shrink-0 px-2 py-0.5 text-[10px] font-bold rounded-full bg-teal text-white shadow-sm">
                      {count}
                    </span>
                  )}
                  {isRail && count > 0 && (
                    <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-teal" />
                  )}
                </NavLink>
              );
            })}

            {/* Quick Start Guide entry inside System group */}
            {group.id === 'system' && (
              <button
                onClick={() => {
                  openGuide();
                  if (onCloseMobileDrawer) onCloseMobileDrawer();
                }}
                title={isRail ? `Quick Start Guide (${completedCount}/${totalSteps})` : undefined}
                className={`group relative flex items-center gap-3 px-3 py-2.5 rounded-btn text-xs sm:text-sm font-medium transition-all min-h-[44px] w-full text-left text-slate-300 hover:bg-navy-light/40 hover:text-white dark:hover:bg-slate-800/50 ${
                  isRail ? 'justify-center px-2' : ''
                }`}
              >
                <Compass className="w-4 h-4 flex-shrink-0 text-teal group-hover:text-white animate-spin-slow" />
                {!isRail && <span className="truncate flex-1">Quick Start</span>}
                {!isRail && (
                  <span className="flex-shrink-0 px-2 py-0.5 text-[10px] font-bold rounded-full bg-teal/20 text-teal-300 border border-teal/40">
                    {completedCount}/{totalSteps}
                  </span>
                )}
                {isRail && (
                  <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-teal" />
                )}
              </button>
            )}
          </div>
        );
      })}
    </div>
  );

  const sidebarContent = (isRail: boolean) => (
    <div className="flex flex-col h-full bg-navy dark:bg-sidebar text-white select-none border-r border-navy-dark dark:border-border">
      {/* Brand Header */}
      <div className={`h-16 px-4 flex items-center justify-between border-b border-navy-light/30 dark:border-border flex-shrink-0 ${isRail ? 'justify-center' : ''}`}>
        <div className="flex items-center gap-2.5 overflow-hidden">
          <div className="w-8 h-8 rounded-lg bg-teal flex items-center justify-center text-white shadow-sm flex-shrink-0">
            <Shield className="w-4 h-4" />
          </div>
          {!isRail && (
            <div className="min-w-0">
              <h1 className="font-bold text-sm tracking-tight leading-none text-white truncate">
                HandoverLedger
              </h1>
              <p className="text-[9px] text-teal-300 uppercase font-semibold tracking-wider mt-1 truncate">
                Verifiable Handover
              </p>
            </div>
          )}
        </div>

        {/* Collapse / Expand toggle for desktop */}
        {!isRail ? (
          <button
            onClick={toggleCollapse}
            className="hidden lg:flex p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-navy-light/40 transition-colors"
            title="Collapse sidebar to icon rail"
            aria-label="Collapse sidebar"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
        ) : (
          <button
            onClick={toggleCollapse}
            className="hidden lg:flex p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-navy-light/40 transition-colors"
            title="Expand sidebar"
            aria-label="Expand sidebar"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Nav items */}
      {renderNavList(isRail)}

      {/* Footer: Strict clearance model chip */}
      <div className="p-3 border-t border-navy-light/30 dark:border-border bg-navy-dark/60 dark:bg-slate-950/40 text-[11px] text-slate-400 flex-shrink-0">
        {!isRail ? (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1">
                <Lock className="w-3 h-3 text-slate-400" />
                Clearance
              </span>
              <ClearanceBadge clearance={roleConfig.clearance} size="sm" />
            </div>
            <p className="text-[10px] leading-relaxed text-slate-400">
              Strict clearance model: restricted data never leaves the database for lower roles.
            </p>
          </div>
        ) : (
          <div className="flex justify-center" title={`Clearance: ${roleConfig.clearanceLabel}`}>
            <Lock className="w-4 h-4 text-slate-400" />
          </div>
        )}
      </div>
    </div>
  );

  return (
    <>
      {/* 1. Desktop & Tablet: Persistent Sidebar */}
      {/* >= 1280px (xl): w-64 full sidebar (or 72px if collapsed) */}
      {/* 1024px - 1279px (lg): 72px rail sidebar */}
      <aside
        className={`hidden lg:flex flex-col flex-shrink-0 transition-all duration-200 z-sidebar h-screen sticky top-0 ${
          isCollapsed ? 'w-[72px]' : 'lg:w-[72px] xl:w-64'
        }`}
      >
        <div className="h-full w-full">
          {/* On xl, if not manually collapsed, render full; on lg or if collapsed, render rail */}
          <div className="h-full xl:block hidden">
            {isCollapsed ? sidebarContent(true) : sidebarContent(false)}
          </div>
          <div className="h-full xl:hidden block">{sidebarContent(true)}</div>
        </div>
      </aside>

      {/* 2. Mobile & Tablet (< 1024px): Off-canvas Drawer */}
      {isMobileDrawerOpen && (
        <div className="fixed inset-0 z-drawer lg:hidden overflow-hidden" role="dialog" aria-modal="true">
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-slate-950/70 backdrop-blur-sm transition-opacity"
            onClick={onCloseMobileDrawer}
            aria-hidden="true"
          />

          <div className="fixed inset-y-0 left-0 max-w-full flex pr-10">
            <div
              className="w-72 max-w-[85vw] h-full shadow-2xl flex flex-col bg-navy dark:bg-sidebar"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Mobile Drawer Header with Close Button */}
              <div className="h-16 px-4 flex items-center justify-between border-b border-navy-light/30 dark:border-border">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-teal flex items-center justify-center text-white shadow-sm">
                    <Shield className="w-4 h-4" />
                  </div>
                  <div>
                    <h2 className="font-bold text-sm text-white">HandoverLedger</h2>
                    <p className="text-[10px] text-teal-300 font-medium">
                      {isDemo ? 'Campus Connect' : isOwn ? 'Your project' : 'Workspace'}
                    </p>
                  </div>
                </div>
                <button
                  onClick={onCloseMobileDrawer}
                  className="p-2 min-w-[44px] min-h-[44px] flex items-center justify-center text-slate-300 hover:text-white rounded-btn focus-visible:ring-2 focus-visible:ring-teal"
                  aria-label="Close navigation drawer"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Compact project chip for mobile */}
              {!isEmpty && (
                <div className="px-4 py-2.5 bg-navy-dark/40 dark:bg-slate-950/30 border-b border-navy-light/20 text-xs text-slate-300">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block">Current Handover</span>
                  <span className="font-medium text-white truncate block">
                    {isDemo ? 'Campus Connect • Arjun Mehta' : 'Your project'}
                  </span>
                </div>
              )}

              {/* Navigation links (Full mode for mobile drawer) */}
              {renderNavList(false)}

              {/* Footer clearance banner */}
              <div className="p-4 border-t border-navy-light/30 dark:border-border bg-navy-dark/60 text-xs text-slate-400 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1">
                    <Lock className="w-3 h-3 text-slate-400" />
                    Clearance
                  </span>
                  <ClearanceBadge clearance={roleConfig.clearance} size="sm" />
                </div>
                <p className="text-[10px] leading-relaxed text-slate-400">
                  Strict clearance model: restricted data never leaves the database for lower roles.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
