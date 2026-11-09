import React, { useState, useRef, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Menu,
  Sun,
  Moon,
  Laptop,
  MoreVertical,
  RefreshCw,
  Settings as SettingsIcon,
  Command,
  Info,
  X,
  AlertTriangle,
  ChevronDown,
  Lock,
} from 'lucide-react';
import { useRole, ROLE_DETAILS } from '../../context/RoleContext';
import { useTheme } from '../../context/ThemeContext';
import { useToast } from '../../context/ToastContext';
import { api } from '../../api/client';
import { DemoRole } from '../../types';
import { Button } from '../common/Button';
import { Modal } from '../common/Modal';
import { ALL_NAV_ITEMS } from '../../config/navigation';

interface TopbarProps {
  onToggleMobileDrawer: () => void;
  onOpenCommandPalette?: () => void;
}

export const Topbar: React.FC<TopbarProps> = ({
  onToggleMobileDrawer,
  onOpenCommandPalette,
}) => {
  const { role, setRole, roleConfig } = useRole();
  const { theme, resolvedTheme, cycleTheme } = useTheme();
  const { success, error } = useToast();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const location = useLocation();

  const [showBanner, setShowBanner] = useState<boolean>(() => {
    return localStorage.getItem('handover_demo_banner_dismissed') !== 'true';
  });
  const [showResetModal, setShowResetModal] = useState(false);
  const [showOverflowMenu, setShowOverflowMenu] = useState(false);
  const [showShortcutsModal, setShowShortcutsModal] = useState(false);
  const overflowRef = useRef<HTMLDivElement>(null);

  // Close overflow menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (overflowRef.current && !overflowRef.current.contains(e.target as Node)) {
        setShowOverflowMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Fetch project state for project chip and status chip
  const { data: project } = useQuery({
    queryKey: ['project'],
    queryFn: api.getProject,
    staleTime: 5000,
  });

  const resetMutation = useMutation({
    mutationFn: api.resetDemo,
    onSuccess: () => {
      queryClient.invalidateQueries();
      setShowResetModal(false);
      success('Demo Reset', 'All project data has been cleared to fresh initial state.');
    },
    onError: (err: any) => {
      error('Reset Failed', err.message);
    },
  });

  const handleDismissBanner = () => {
    setShowBanner(false);
    localStorage.setItem('handover_demo_banner_dismissed', 'true');
  };

  const rolesList: DemoRole[] = ['lead', 'departing', 'developer', 'coordinator'];

  // Handover status config
  const statusConfig: Record<string, { label: string; bg: string; text: string }> = {
    not_started: { label: 'Not Started', bg: 'bg-slate-100 dark:bg-slate-800', text: 'text-slate-600 dark:text-slate-400' },
    draft: { label: 'Draft', bg: 'bg-amber-100 dark:bg-amber-950/60', text: 'text-amber-800 dark:text-amber-300' },
    in_review: { label: 'In Review', bg: 'bg-blue-100 dark:bg-blue-950/60', text: 'text-blue-800 dark:text-blue-300' },
    approved: { label: 'Approved & Released', bg: 'bg-emerald-100 dark:bg-emerald-950/60', text: 'text-emerald-800 dark:text-emerald-300' },
    sent_back: { label: 'Sent Back for Changes', bg: 'bg-rose-100 dark:bg-rose-950/60', text: 'text-rose-800 dark:text-rose-300' },
  };

  const currentStatus = statusConfig[project?.handover_status || 'draft'] || statusConfig.draft;

  // Determine current page title
  const currentNavItem = ALL_NAV_ITEMS.find((item) =>
    item.to === '/' ? location.pathname === '/' : location.pathname.startsWith(item.to)
  );
  const pageTitle = currentNavItem ? currentNavItem.label : 'HandoverLedger';

  return (
    <header className="bg-surface border-b border-border z-20 flex flex-col flex-shrink-0 sticky top-0">
      {/* 1. Dismissible Demo Mode Banner */}
      {showBanner && (
        <div className="bg-slate-900 text-slate-100 px-3 sm:px-4 py-2 text-xs flex items-center justify-between border-b border-slate-800">
          <div className="flex items-center gap-2 overflow-hidden">
            <Info className="w-4 h-4 text-teal flex-shrink-0" />
            <span className="truncate hidden sm:inline">
              <strong>Demo mode:</strong> Roles are simulated via header{' '}
              <code className="bg-slate-800 px-1 py-0.5 rounded text-teal-300 font-mono">X-Demo-Role</code>. No login required. All data is synthetic.
            </span>
            <span className="truncate sm:hidden text-[11px]">
              <strong>Demo mode:</strong> Simulated roles (X-Demo-Role). All data synthetic.
            </span>
          </div>
          <button
            onClick={handleDismissBanner}
            className="text-slate-400 hover:text-white p-1 min-w-[32px] min-h-[32px] flex items-center justify-center rounded transition-colors"
            title="Dismiss demo banner"
            aria-label="Dismiss banner"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* 2. Main Top Bar */}
      <div className="h-16 px-3 sm:px-6 flex items-center justify-between gap-2 sm:gap-4">
        {/* Left: Hamburger (mobile/tablet < 1024px) + Page Title + Project Chip */}
        <div className="flex items-center gap-2 sm:gap-3 min-w-0">
          {/* Hamburger button for screens below 1024px */}
          <button
            onClick={onToggleMobileDrawer}
            className="lg:hidden p-2 min-w-[44px] min-h-[44px] flex items-center justify-center text-text-muted hover:text-text-main rounded-btn hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            title="Open navigation menu"
            aria-label="Open navigation menu"
          >
            <Menu className="w-5 h-5" />
          </button>

          {/* Current Page Title */}
          <h1 className="text-base sm:text-lg font-bold text-text-main truncate max-w-[140px] sm:max-w-[220px] md:max-w-none">
            {pageTitle}
          </h1>

          {/* Project Chip: hidden on mobile (< 640px), visible from sm */}
          <div className="hidden sm:flex items-center gap-2 bg-slate-100 dark:bg-slate-800/80 border border-border px-2.5 py-1 rounded-btn text-xs">
            <span className="font-semibold text-text-main">Campus Connect</span>
            <span className="text-text-muted">•</span>
            <span className="text-text-muted truncate max-w-[120px] md:max-w-none">
              {project?.departing_member || 'Arjun Mehta'}
            </span>
          </div>

          {/* Handover Status Chip */}
          <div
            className={`hidden md:inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold ${currentStatus.bg} ${currentStatus.text}`}
          >
            {currentStatus.label}
          </div>
        </div>

        {/* Right: Role Switcher + Theme Toggle + Overflow Menu */}
        <div className="flex items-center gap-1.5 sm:gap-2.5">
          {/* A. Role Switcher: Segmented Control on >= 1024px */}
          <div className="hidden lg:flex items-center bg-slate-100 dark:bg-slate-800 border border-border p-1 rounded-btn">
            <span className="text-[10px] font-bold text-text-muted uppercase px-2 tracking-wider">
              Role:
            </span>
            <div className="flex items-center gap-0.5">
              {rolesList.map((r) => {
                const cfg = ROLE_DETAILS[r];
                const isSelected = role === r;
                return (
                  <button
                    key={r}
                    onClick={() => setRole(r)}
                    title={`${cfg.label} (${cfg.name}): ${cfg.clearanceLabel}`}
                    className={`px-2.5 py-1 rounded-btn text-xs font-medium transition-all min-h-[32px] flex items-center gap-1.5 ${
                      isSelected
                        ? 'bg-surface text-navy dark:text-teal font-semibold shadow-soft border border-border'
                        : 'text-text-muted hover:text-text-main hover:bg-slate-200/60 dark:hover:bg-slate-700/60'
                    }`}
                  >
                    <span>{cfg.label.replace(' Member', '')}</span>
                    <span
                      className={`inline-block w-2 h-2 rounded-full ${
                        cfg.clearance === 1
                          ? 'bg-emerald-500'
                          : cfg.clearance === 2
                          ? 'bg-blue-500'
                          : 'bg-rose-500'
                      }`}
                    />
                  </button>
                );
              })}
            </div>
          </div>

          {/* B. Role Switcher: Compact Dropdown for screens < 1024px */}
          <div className="lg:hidden relative">
            <select
              value={role}
              onChange={(e) => setRole(e.target.value as DemoRole)}
              className="appearance-none bg-slate-100 dark:bg-slate-800 border border-border rounded-btn pl-2.5 pr-7 py-1.5 text-xs font-medium text-text-main min-h-[44px] focus:outline-none focus:ring-1 focus:ring-navy"
              aria-label="Switch active demo role"
            >
              {rolesList.map((r) => {
                const cfg = ROLE_DETAILS[r];
                return (
                  <option key={r} value={r}>
                    {cfg.label} ({cfg.clearanceLabel.split(':')[0]})
                  </option>
                );
              })}
            </select>
            <ChevronDown className="w-3.5 h-3.5 pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-text-muted" />
          </div>

          {/* Theme Toggle Button (Light -> Dark -> System) */}
          <button
            onClick={cycleTheme}
            className="p-2 min-w-[40px] min-h-[40px] sm:min-w-[44px] sm:min-h-[44px] flex items-center justify-center text-text-muted hover:text-text-main rounded-btn hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors focus-visible:ring-2 focus-visible:ring-navy"
            title={`Theme: ${theme.toUpperCase()} (Click to toggle)`}
            aria-label={`Toggle theme. Current: ${theme}`}
          >
            {theme === 'system' ? (
              <Laptop className="w-4 h-4" />
            ) : resolvedTheme === 'dark' ? (
              <Moon className="w-4 h-4 text-teal" />
            ) : (
              <Sun className="w-4 h-4 text-amber-500" />
            )}
          </button>

          {/* Overflow Menu "..." */}
          <div className="relative" ref={overflowRef}>
            <button
              onClick={() => setShowOverflowMenu(!showOverflowMenu)}
              className="p-2 min-w-[40px] min-h-[40px] sm:min-w-[44px] sm:min-h-[44px] flex items-center justify-center text-text-muted hover:text-text-main rounded-btn hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors focus-visible:ring-2 focus-visible:ring-navy"
              title="More actions"
              aria-label="More actions"
              aria-expanded={showOverflowMenu}
            >
              <MoreVertical className="w-4 h-4" />
            </button>

            {/* Dropdown Popover */}
            {showOverflowMenu && (
              <div className="absolute right-0 mt-1 w-52 bg-surface rounded-card border border-border shadow-card py-1 z-50 text-sm">
                <button
                  onClick={() => {
                    setShowOverflowMenu(false);
                    setShowResetModal(true);
                  }}
                  className="w-full flex items-center gap-2.5 px-3.5 py-2 text-xs font-medium text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 text-left min-h-[44px] sm:min-h-0"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>Reset Demo Data</span>
                </button>
                <button
                  onClick={() => {
                    setShowOverflowMenu(false);
                    navigate('/settings');
                  }}
                  className="w-full flex items-center gap-2.5 px-3.5 py-2 text-xs font-medium text-text-main hover:bg-slate-100 dark:hover:bg-slate-800 text-left min-h-[44px] sm:min-h-0"
                >
                  <SettingsIcon className="w-3.5 h-3.5 text-text-muted" />
                  <span>Settings & Preferences</span>
                </button>
                <button
                  onClick={() => {
                    setShowOverflowMenu(false);
                    setShowShortcutsModal(true);
                  }}
                  className="w-full flex items-center gap-2.5 px-3.5 py-2 text-xs font-medium text-text-main hover:bg-slate-100 dark:hover:bg-slate-800 text-left min-h-[44px] sm:min-h-0"
                >
                  <Command className="w-3.5 h-3.5 text-text-muted" />
                  <span>Keyboard Shortcuts</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Reset Confirmation Modal */}
      <Modal
        isOpen={showResetModal}
        onClose={() => setShowResetModal(false)}
        title="Reset Demo Data?"
        description="This will clear all sources, claims, questions, and approvals from the local SQLite database."
        footer={
          <>
            <Button variant="outline" size="sm" onClick={() => setShowResetModal(false)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              size="sm"
              isLoading={resetMutation.isPending}
              onClick={() => resetMutation.mutate()}
            >
              Reset Everything
            </Button>
          </>
        }
      >
        <div className="p-2 flex items-start gap-3 text-text-main text-sm">
          <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
          <p>
            Are you sure you want to reset? You can reload the synthetic demo anytime by clicking{' '}
            <strong>&quot;Load Demo Project&quot;</strong> on the dashboard or sources page.
          </p>
        </div>
      </Modal>

      {/* Shortcuts Modal */}
      <Modal
        isOpen={showShortcutsModal}
        onClose={() => setShowShortcutsModal(false)}
        title="Keyboard Shortcuts"
        description="Quick navigation shortcuts across HandoverLedger."
        footer={
          <Button variant="primary" size="sm" onClick={() => setShowShortcutsModal(false)}>
            Close
          </Button>
        }
      >
        <div className="space-y-3 text-xs text-text-main">
          <div className="flex items-center justify-between p-2 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-border">
            <span>Open Command Palette</span>
            <kbd className="px-2 py-1 bg-surface border border-border rounded font-mono font-bold shadow-soft">
              Ctrl + K / ⌘K
            </kbd>
          </div>
          <div className="flex items-center justify-between p-2 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-border">
            <span>Toggle Theme (Light / Dark / System)</span>
            <kbd className="px-2 py-1 bg-surface border border-border rounded font-mono font-bold shadow-soft">
              Shift + T
            </kbd>
          </div>
          <div className="flex items-center justify-between p-2 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-border">
            <span>Close Active Modal or Drawer</span>
            <kbd className="px-2 py-1 bg-surface border border-border rounded font-mono font-bold shadow-soft">
              Escape
            </kbd>
          </div>
        </div>
      </Modal>
    </header>
  );
};
