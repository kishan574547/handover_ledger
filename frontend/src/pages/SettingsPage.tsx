import React, { useState, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Sun,
  Moon,
  Laptop,
  Check,
  ShieldCheck,
  RefreshCw,
  Trash2,
  Lock,
  Eye,
  Info,
  Command,
  Sparkles,
  Sliders,
  Database,
  Cpu,
} from 'lucide-react';
import { useTheme, Theme } from '../context/ThemeContext';
import { useRole, ROLE_DETAILS } from '../context/RoleContext';
import { useToast } from '../context/ToastContext';
import { api } from '../api/client';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Modal } from '../components/common/Modal';
import { DemoRole } from '../types';

export const SettingsPage: React.FC = () => {
  const { theme, setTheme } = useTheme();
  const { role, setRole } = useRole();
  const { success, error, info } = useToast();
  const queryClient = useQueryClient();

  useEffect(() => {
    document.title = 'Settings & Preferences | HandoverLedger';
  }, []);

  // 1. Density preference
  const [density, setDensity] = useState<'comfortable' | 'compact'>(() => {
    return (localStorage.getItem('handover_density') as any) || 'comfortable';
  });

  const handleDensityChange = (val: 'comfortable' | 'compact') => {
    setDensity(val);
    localStorage.setItem('handover_density', val);
    if (val === 'compact') {
      document.documentElement.classList.add('density-compact');
    } else {
      document.documentElement.classList.remove('density-compact');
    }
    info('Density Updated', `Interface set to ${val} mode.`);
  };

  // 2. Text size preference
  const [textSize, setTextSize] = useState<number>(() => {
    return Number(localStorage.getItem('handover_text_size')) || 100;
  });

  const handleTextSizeChange = (size: number) => {
    setTextSize(size);
    localStorage.setItem('handover_text_size', String(size));
    document.documentElement.style.fontSize = `${size}%`;
    info('Text Size Updated', `Font scale adjusted to ${size}%.`);
  };

  // 3. Reduce motion preference
  const [reduceMotion, setReduceMotion] = useState<boolean>(() => {
    return localStorage.getItem('handover_reduce_motion') === 'true';
  });

  const handleReduceMotionToggle = (enabled: boolean) => {
    setReduceMotion(enabled);
    localStorage.setItem('handover_reduce_motion', String(enabled));
    if (enabled) {
      document.documentElement.classList.add('force-reduced-motion');
    } else {
      document.documentElement.classList.remove('force-reduced-motion');
    }
  };

  // 4. Default role preference
  const [defaultRole, setDefaultRole] = useState<DemoRole>(() => {
    return (localStorage.getItem('handover_default_role') as DemoRole) || 'lead';
  });

  const handleDefaultRoleChange = (r: DemoRole) => {
    setDefaultRole(r);
    localStorage.setItem('handover_default_role', r);
    info('Default Role Saved', `Future visits will initialize as ${ROLE_DETAILS[r].label}.`);
  };

  // 5. Demo preferences
  const [showDemoBanner, setShowDemoBanner] = useState<boolean>(() => {
    return localStorage.getItem('handover_demo_banner_dismissed') !== 'true';
  });

  const handleDemoBannerToggle = (val: boolean) => {
    setShowDemoBanner(val);
    if (val) {
      localStorage.removeItem('handover_demo_banner_dismissed');
    } else {
      localStorage.setItem('handover_demo_banner_dismissed', 'true');
    }
  };

  const [showJudgeGuide, setShowJudgeGuide] = useState<boolean>(() => {
    return localStorage.getItem('handover_show_judge_guide') !== 'false';
  });

  const handleJudgeGuideToggle = (val: boolean) => {
    setShowJudgeGuide(val);
    localStorage.setItem('handover_show_judge_guide', String(val));
    window.dispatchEvent(new Event('judge_guide_pref_changed'));
  };

  // Reset Modal state
  const [showResetModal, setShowResetModal] = useState(false);
  const resetMutation = useMutation({
    mutationFn: api.resetDemo,
    onSuccess: () => {
      queryClient.invalidateQueries();
      setShowResetModal(false);
      success('Demo Reset', 'All data has been reset to empty initial state.');
    },
    onError: (err: any) => error('Reset Failed', err.message),
  });

  const handleClearSettings = () => {
    localStorage.removeItem('handover_theme');
    localStorage.removeItem('handover_density');
    localStorage.removeItem('handover_text_size');
    localStorage.removeItem('handover_reduce_motion');
    localStorage.removeItem('handover_default_role');
    localStorage.removeItem('handover_demo_banner_dismissed');
    localStorage.removeItem('handover_show_judge_guide');
    localStorage.removeItem('handover_sidebar_collapsed');
    document.documentElement.style.fontSize = '100%';
    document.documentElement.classList.remove('density-compact', 'force-reduced-motion');
    setTheme('system');
    setDensity('comfortable');
    setTextSize(100);
    setReduceMotion(false);
    setDefaultRole('lead');
    setShowDemoBanner(true);
    setShowJudgeGuide(true);
    success('Settings Cleared', 'Preferences have been restored to defaults.');
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div>
        <h2 className="page-title text-text-main">Settings & Preferences</h2>
        <p className="text-sm text-text-muted mt-1">
          Customise interface appearance, demo defaults, accessibility, and review system privacy rules.
        </p>
      </div>

      {/* 1. Appearance Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sliders className="w-4 h-4 text-navy dark:text-teal" />
            <span>Appearance & Theme</span>
          </CardTitle>
          <CardDescription>Select visual styling, interface density, and text sizing.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Theme selector cards */}
          <div>
            <label className="text-xs font-semibold text-text-muted uppercase tracking-wider block mb-2">
              Color Theme
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {[
                { id: 'light' as Theme, label: 'Light Mode', icon: Sun, desc: 'Clean high-contrast daytime interface' },
                { id: 'dark' as Theme, label: 'Dark Mode', icon: Moon, desc: 'Deep navy background for low light' },
                { id: 'system' as Theme, label: 'System Default', icon: Laptop, desc: 'Follows your operating system theme' },
              ].map((item) => {
                const Icon = item.icon;
                const isSelected = theme === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => setTheme(item.id)}
                    className={`p-4 rounded-btn border text-left transition-all relative flex flex-col justify-between min-h-[96px] ${
                      isSelected
                        ? 'border-navy dark:border-teal bg-navy/5 dark:bg-teal/10 shadow-soft ring-1 ring-navy dark:ring-teal'
                        : 'border-border bg-surface hover:border-slate-300 dark:hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center justify-between w-full">
                      <div className="flex items-center gap-2">
                        <Icon className={`w-4 h-4 ${isSelected ? 'text-navy dark:text-teal' : 'text-text-muted'}`} />
                        <span className="text-sm font-semibold text-text-main">{item.label}</span>
                      </div>
                      {isSelected && <Check className="w-4 h-4 text-navy dark:text-teal" />}
                    </div>
                    <p className="text-xs text-text-muted mt-2">{item.desc}</p>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Density & Text Size */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 pt-2 border-t border-border">
            {/* Density */}
            <div>
              <label className="text-xs font-semibold text-text-muted uppercase tracking-wider block mb-2">
                Interface Density
              </label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => handleDensityChange('comfortable')}
                  className={`px-3 py-2 rounded-btn border text-xs font-medium transition-all min-h-[44px] ${
                    density === 'comfortable'
                      ? 'border-navy dark:border-teal bg-navy/10 dark:bg-teal/20 text-navy dark:text-teal font-semibold'
                      : 'border-border bg-surface text-text-main hover:bg-slate-50 dark:hover:bg-slate-800'
                  }`}
                >
                  Comfortable
                </button>
                <button
                  onClick={() => handleDensityChange('compact')}
                  className={`px-3 py-2 rounded-btn border text-xs font-medium transition-all min-h-[44px] ${
                    density === 'compact'
                      ? 'border-navy dark:border-teal bg-navy/10 dark:bg-teal/20 text-navy dark:text-teal font-semibold'
                      : 'border-border bg-surface text-text-main hover:bg-slate-50 dark:hover:bg-slate-800'
                  }`}
                >
                  Compact
                </button>
              </div>
            </div>

            {/* Text Size */}
            <div>
              <label className="text-xs font-semibold text-text-muted uppercase tracking-wider block mb-2">
                Text Scaling ({textSize}%)
              </label>
              <div className="grid grid-cols-4 gap-1.5">
                {[90, 100, 110, 125].map((sz) => (
                  <button
                    key={sz}
                    onClick={() => handleTextSizeChange(sz)}
                    className={`px-2 py-2 rounded-btn border text-xs font-medium transition-all min-h-[44px] ${
                      textSize === sz
                        ? 'border-navy dark:border-teal bg-navy/10 dark:bg-teal/20 text-navy dark:text-teal font-semibold'
                        : 'border-border bg-surface text-text-main hover:bg-slate-50 dark:hover:bg-slate-800'
                    }`}
                  >
                    {sz}%
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Reduce Motion */}
          <div className="pt-2 border-t border-border flex items-center justify-between">
            <div>
              <h4 className="text-sm font-semibold text-text-main">Reduce Motion</h4>
              <p className="text-xs text-text-muted">Minimise transition animations and motion effects.</p>
            </div>
            <input
              type="checkbox"
              id="reduce-motion"
              checked={reduceMotion}
              onChange={(e) => handleReduceMotionToggle(e.target.checked)}
              className="w-4 h-4 rounded text-navy dark:text-teal focus:ring-navy cursor-pointer"
            />
          </div>
        </CardContent>
      </Card>

      {/* 2. Demo Preferences Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-navy dark:text-teal" />
            <span>Demo Preferences</span>
          </CardTitle>
          <CardDescription>Tailor simulated role defaults and assistance guides.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Default Role Selection */}
          <div>
            <label className="text-xs font-semibold text-text-muted uppercase tracking-wider block mb-2">
              Default Simulated Role on Open
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {(['lead', 'departing', 'developer', 'coordinator'] as DemoRole[]).map((r) => {
                const cfg = ROLE_DETAILS[r];
                const isSelected = defaultRole === r;
                return (
                  <button
                    key={r}
                    onClick={() => handleDefaultRoleChange(r)}
                    className={`p-3 rounded-btn border text-left flex items-center justify-between min-h-[44px] transition-all ${
                      isSelected
                        ? 'border-navy dark:border-teal bg-navy/5 dark:bg-teal/10'
                        : 'border-border bg-surface hover:bg-slate-50 dark:hover:bg-slate-800'
                    }`}
                  >
                    <div>
                      <span className="text-xs font-semibold text-text-main block">{cfg.label}</span>
                      <span className="text-[11px] text-text-muted">{cfg.clearanceLabel}</span>
                    </div>
                    {isSelected && <Check className="w-4 h-4 text-navy dark:text-teal" />}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Banner & Guide Toggles */}
          <div className="space-y-3 pt-3 border-t border-border">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-sm font-semibold text-text-main">Show Demo Mode Banner</h4>
                <p className="text-xs text-text-muted">Top bar banner showing simulated role header.</p>
              </div>
              <input
                type="checkbox"
                checked={showDemoBanner}
                onChange={(e) => handleDemoBannerToggle(e.target.checked)}
                className="w-4 h-4 rounded text-navy dark:text-teal focus:ring-navy cursor-pointer"
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-sm font-semibold text-text-main">Show Judge Quick-Start Guide</h4>
                <p className="text-xs text-text-muted">Floating interactive checklist tracking full handover journey.</p>
              </div>
              <input
                type="checkbox"
                checked={showJudgeGuide}
                onChange={(e) => handleJudgeGuideToggle(e.target.checked)}
                className="w-4 h-4 rounded text-navy dark:text-teal focus:ring-navy cursor-pointer"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 3. Data & Storage Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="w-4 h-4 text-navy dark:text-teal" />
            <span>Data & Local Storage</span>
          </CardTitle>
          <CardDescription>Reset demo content or revert custom settings.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3.5 rounded-btn bg-slate-50 dark:bg-slate-900/40 border border-border">
            <div>
              <h4 className="text-xs font-semibold text-text-main">Reset Demo Database</h4>
              <p className="text-[11px] text-text-muted">Clears all claims, sources, and questions back to clean initial state.</p>
            </div>
            <Button variant="danger" size="sm" onClick={() => setShowResetModal(true)} leftIcon={<RefreshCw className="w-3.5 h-3.5" />}>
              Reset Demo Data
            </Button>
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3.5 rounded-btn bg-slate-50 dark:bg-slate-900/40 border border-border">
            <div>
              <h4 className="text-xs font-semibold text-text-main">Clear Saved Preferences</h4>
              <p className="text-[11px] text-text-muted">Resets theme, density, and local flags back to default values.</p>
            </div>
            <Button variant="outline" size="sm" onClick={handleClearSettings} leftIcon={<Trash2 className="w-3.5 h-3.5 text-text-muted" />}>
              Clear Settings
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 4. Privacy & Clearance Model */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Lock className="w-4 h-4 text-navy dark:text-teal" />
            <span>Privacy & Security Architecture</span>
          </CardTitle>
          <CardDescription>How HandoverLedger protects team secrets and respects clearances.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-xs text-text-main leading-relaxed">
          <div className="p-3 rounded-btn bg-blue-50/60 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-900 text-blue-900 dark:text-blue-200">
            <strong>Clearance Filtering at Database Query Layer:</strong> All SQL queries filter rows with{' '}
            <code className="font-mono bg-blue-100 dark:bg-blue-900/60 px-1 py-0.5 rounded">Claim.clearance &lt;= max_clearance</code>.
            Restricted confidential items are NEVER selected from the database or sent across the network to unauthorized roles.
          </div>
          <div className="p-3 rounded-btn bg-emerald-50/60 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-900 text-emerald-900 dark:text-emerald-200">
            <strong>Pre-Ingestion Regex Masking:</strong> Sensitive patterns like API keys (AIza..., sk-..., ghp_...), passwords, private keys, emails, and phone numbers are automatically sanitized into <code className="font-mono bg-emerald-100 dark:bg-emerald-900/60 px-1 py-0.5 rounded">[MASKED:type]</code> before any AI call.
          </div>
          <div className="p-3 rounded-btn bg-slate-50 dark:bg-slate-900/40 border border-border text-text-muted">
            <strong>Synthetic Demo Project:</strong> All names, phone numbers, and credentials in the &quot;Campus Connect&quot; demo are synthetic and intended for local testing only.
          </div>
        </CardContent>
      </Card>

      {/* 5. About */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Cpu className="w-4 h-4 text-navy dark:text-teal" />
            <span>About HandoverLedger</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-xs text-text-muted">
          <p>
            <strong className="text-text-main">Version:</strong> 1.2.0 (Hackathon Edition)
          </p>
          <p>
            <strong className="text-text-main">Stack:</strong> React 18, Vite, TypeScript, Tailwind CSS, TanStack Query, FastAPI, SQLAlchemy 2, SQLite / Supabase, Google GenAI (Gemini 2.5 Flash), RapidFuzz.
          </p>
          <p className="pt-1 text-[11px] text-teal font-medium">
            Built with AI assistance (Antigravity, Gemini).
          </p>
        </CardContent>
      </Card>

      {/* Reset Confirmation Modal */}
      <Modal
        isOpen={showResetModal}
        onClose={() => setShowResetModal(false)}
        title="Confirm Demo Reset"
        description="Are you sure you want to delete all loaded sources, verified claims, and interview questions?"
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
              Confirm Reset
            </Button>
          </>
        }
      >
        <p className="text-xs text-text-main">
          This will wipe the SQLite database tables and return the project to an empty state. You can reload the synthetic demo anytime from the Dashboard.
        </p>
      </Modal>
    </div>
  );
};

