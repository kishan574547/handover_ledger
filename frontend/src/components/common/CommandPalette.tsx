import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Search,
  ArrowRight,
  FileSpreadsheet,
  Moon,
  Sun,
  Compass,
  User,
  Shield,
  Play,
  RefreshCw,
  X,
  Lock,
} from 'lucide-react';
import { useRole, ROLE_DETAILS } from '../../context/RoleContext';
import { useTheme } from '../../context/ThemeContext';
import { ALL_NAV_ITEMS } from '../../config/navigation';
import { api } from '../../api/client';
import { DemoRole, ClaimItem } from '../../types';
import { StatusBadge, ClearanceBadge } from './Badge';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({ isOpen, onClose }) => {
  const navigate = useNavigate();
  const { role, setRole, canLead } = useRole();
  const { theme, cycleTheme } = useTheme();

  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus input on open
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
      setQuery('');
      setSelectedIndex(0);
    }
  }, [isOpen]);

  // Global Ctrl+K / Cmd+K listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        if (isOpen) onClose();
        else onClose(); // parent handles toggling
      }
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Query claims matching search string within current clearance
  const { data: claimsData } = useQuery({
    queryKey: ['claims-search', query],
    queryFn: () => api.getClaims({ q: query, limit: 6 }),
    enabled: isOpen && query.trim().length >= 2,
    staleTime: 5000,
  });

  if (!isOpen) return null;

  // Filter allowed navigation pages
  const allowedNav = ALL_NAV_ITEMS.filter((item) => item.allowedRoles.includes(role));
  const filteredNav = allowedNav.filter((item) =>
    item.label.toLowerCase().includes(query.toLowerCase())
  );

  // Action commands
  const actions = [
    {
      id: 'action-quick-start',
      title: 'Open Quick-Start Guide (Checklist)',
      icon: <Compass className="w-4 h-4 text-teal" />,
      run: () => {
        window.dispatchEvent(new CustomEvent('open_judge_guide'));
        onClose();
      },
    },
    {
      id: 'action-theme',
      title: `Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`,
      icon: theme === 'dark' ? <Sun className="w-4 h-4 text-amber-500" /> : <Moon className="w-4 h-4 text-teal" />,
      run: () => {
        cycleTheme();
        onClose();
      },
    },
    ...(canLead
      ? [
          {
            id: 'action-analysis',
            title: 'Run AI Reconstruction Pipeline',
            icon: <Play className="w-4 h-4 text-emerald-600" />,
            run: () => {
              navigate('/sources');
              onClose();
            },
          },
        ]
      : []),
    {
      id: 'action-role-lead',
      title: 'Switch Role to Project Lead (Level 3 Clearance)',
      icon: <User className="w-4 h-4 text-rose-500" />,
      run: () => {
        setRole('lead');
        onClose();
      },
    },
    {
      id: 'action-role-dev',
      title: 'Switch Role to Successor Developer (Level 2 Clearance)',
      icon: <User className="w-4 h-4 text-blue-500" />,
      run: () => {
        setRole('developer');
        onClose();
      },
    },
    {
      id: 'action-role-coord',
      title: 'Switch Role to Coordinator (Level 1 Clearance)',
      icon: <User className="w-4 h-4 text-emerald-500" />,
      run: () => {
        setRole('coordinator');
        onClose();
      },
    },
  ].filter((a) => a.title.toLowerCase().includes(query.toLowerCase()));

  const claimsList: ClaimItem[] = claimsData?.claims || [];

  // Flattened items for keyboard navigation
  const allSelectable = [
    ...filteredNav.map((n) => ({ type: 'nav', data: n })),
    ...actions.map((a) => ({ type: 'action', data: a })),
    ...claimsList.map((c) => ({ type: 'claim', data: c })),
  ];

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % Math.max(1, allSelectable.length));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + allSelectable.length) % Math.max(1, allSelectable.length));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const current = allSelectable[selectedIndex];
      if (current) {
        if (current.type === 'nav') {
          navigate((current.data as any).to);
          onClose();
        } else if (current.type === 'action') {
          (current.data as any).run();
        } else if (current.type === 'claim') {
          navigate(`/ledger?highlight=${(current.data as any).id}`);
          onClose();
        }
      }
    }
  };

  return (
    <div className="fixed inset-0 z-modal overflow-y-auto p-4 sm:p-6 md:p-20" role="dialog" aria-modal="true">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-slate-950/70 backdrop-blur-sm transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      <div className="relative mx-auto max-w-xl bg-surface rounded-card border border-border shadow-2xl overflow-hidden">
        {/* Search Input Bar */}
        <div className="flex items-center px-4 py-3 border-b border-border gap-3">
          <Search className="w-5 h-5 text-text-muted flex-shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            onKeyDown={handleKeyDown}
            placeholder="Type a page, action, or search claims..."
            className="w-full bg-transparent text-sm text-text-main placeholder:text-text-muted focus:outline-none"
          />
          {query && (
            <button
              onClick={() => setQuery('')}
              className="text-text-muted hover:text-text-main p-1 rounded"
            >
              <X className="w-4 h-4" />
            </button>
          )}
          <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] font-mono text-text-muted bg-slate-100 dark:bg-slate-800 rounded border border-border">
            ESC
          </kbd>
        </div>

        {/* Results List */}
        <div className="max-h-96 overflow-y-auto p-2 space-y-4">
          {/* Navigation Pages */}
          {filteredNav.length > 0 && (
            <div>
              <div className="px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-text-muted">
                Pages
              </div>
              <div className="space-y-0.5">
                {filteredNav.map((item, idx) => {
                  const Icon = item.icon;
                  const itemIndex = idx;
                  const isSelected = selectedIndex === itemIndex;
                  return (
                    <button
                      key={item.id}
                      onClick={() => {
                        navigate(item.to);
                        onClose();
                      }}
                      className={`w-full flex items-center justify-between px-3 py-2 rounded-btn text-xs text-left transition-all ${
                        isSelected
                          ? 'bg-navy/10 dark:bg-teal/20 text-navy dark:text-teal font-semibold'
                          : 'text-text-main hover:bg-slate-100 dark:hover:bg-slate-800'
                      }`}
                    >
                      <div className="flex items-center gap-2.5">
                        <Icon className="w-4 h-4 text-text-muted" />
                        <span>{item.label}</span>
                      </div>
                      <ArrowRight className="w-3.5 h-3.5 text-text-muted" />
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Quick Actions */}
          {actions.length > 0 && (
            <div>
              <div className="px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-text-muted">
                Actions
              </div>
              <div className="space-y-0.5">
                {actions.map((act, idx) => {
                  const itemIndex = filteredNav.length + idx;
                  const isSelected = selectedIndex === itemIndex;
                  return (
                    <button
                      key={act.id}
                      onClick={act.run}
                      className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-btn text-xs text-left transition-all ${
                        isSelected
                          ? 'bg-navy/10 dark:bg-teal/20 text-navy dark:text-teal font-semibold'
                          : 'text-text-main hover:bg-slate-100 dark:hover:bg-slate-800'
                      }`}
                    >
                      {act.icon}
                      <span>{act.title}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Claims search results */}
          {claimsList.length > 0 && (
            <div>
              <div className="px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-text-muted flex items-center justify-between">
                <span>Matching Verified Claims</span>
                <span className="text-[9px] lowercase font-normal">cleared for {role}</span>
              </div>
              <div className="space-y-1">
                {claimsList.map((c, idx) => {
                  const itemIndex = filteredNav.length + actions.length + idx;
                  const isSelected = selectedIndex === itemIndex;
                  return (
                    <button
                      key={c.id}
                      onClick={() => {
                        navigate(`/ledger?highlight=${c.id}`);
                        onClose();
                      }}
                      className={`w-full p-2.5 rounded-btn border text-left transition-all ${
                        isSelected
                          ? 'border-navy dark:border-teal bg-navy/5 dark:bg-teal/10 shadow-soft'
                          : 'border-border bg-surface hover:border-slate-300 dark:hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <StatusBadge status={c.status} size="sm" />
                        <ClearanceBadge clearance={c.clearance} size="sm" />
                        <span className="text-[10px] font-mono text-text-muted truncate">
                          #{c.id.slice(0, 8)}
                        </span>
                      </div>
                      <p className="text-xs text-text-main line-clamp-2 leading-relaxed">{c.text}</p>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* No results */}
          {allSelectable.length === 0 && (
            <div className="py-8 text-center text-xs text-text-muted">
              No matching pages, actions, or claims found.
            </div>
          )}
        </div>

        {/* Footer shortcuts helper */}
        <div className="px-4 py-2 border-t border-border bg-slate-50 dark:bg-slate-900/40 text-[10px] text-text-muted flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span>
              <kbd className="font-mono bg-surface border border-border px-1 rounded">↑↓</kbd> navigate
            </span>
            <span>
              <kbd className="font-mono bg-surface border border-border px-1 rounded">↵</kbd> select
            </span>
          </div>
          <span className="text-teal font-medium">Strict Clearance Isolated</span>
        </div>
      </div>
    </div>
  );
};

