import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  RefreshCw,
  Info,
  X,
  AlertTriangle,
  User,
  Shield,
  Layers,
  ChevronDown,
} from 'lucide-react';
import { useRole, ROLE_DETAILS } from '../../context/RoleContext';
import { useToast } from '../../context/ToastContext';
import { api } from '../../api/client';
import { DemoRole } from '../../types';
import { Button } from '../common/Button';
import { Modal } from '../common/Modal';

export const Topbar: React.FC = () => {
  const { role, setRole, roleConfig } = useRole();
  const { success, error } = useToast();
  const queryClient = useQueryClient();

  const [showBanner, setShowBanner] = useState(true);
  const [showResetModal, setShowResetModal] = useState(false);

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

  const rolesList: DemoRole[] = ['departing', 'lead', 'developer', 'coordinator'];

  // Status Chip styling
  const statusConfig: Record<string, { label: string; bg: string; text: string }> = {
    not_started: { label: 'Not Started', bg: 'bg-slate-100', text: 'text-slate-600' },
    draft: { label: 'Draft', bg: 'bg-amber-100', text: 'text-amber-800' },
    in_review: { label: 'In Review', bg: 'bg-blue-100', text: 'text-blue-800' },
    approved: { label: 'Approved & Released', bg: 'bg-emerald-100', text: 'text-emerald-800' },
    sent_back: { label: 'Sent Back for Changes', bg: 'bg-rose-100', text: 'text-rose-800' },
  };

  const currentStatus = statusConfig[project?.handover_status || 'draft'] || statusConfig.draft;

  return (
    <header className="bg-white border-b border-slate-200 z-20 flex flex-col flex-shrink-0">
      {/* Dismissible Demo Mode Banner */}
      {showBanner && (
        <div className="bg-slate-900 text-slate-100 px-4 py-2 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Info className="w-4 h-4 text-teal-400 flex-shrink-0" />
            <span>
              <strong>Demo mode:</strong> Roles are simulated via header <code className="bg-slate-800 px-1 py-0.5 rounded text-teal-300">X-Demo-Role</code>. No login required. All data is synthetic.
            </span>
          </div>
          <button
            onClick={() => setShowBanner(false)}
            className="text-slate-400 hover:text-white p-0.5"
            title="Dismiss banner"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Main Top Bar */}
      <div className="h-16 px-6 flex items-center justify-between gap-4">
        {/* Left: Project Chip & Handover Status */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-slate-100 border border-slate-200/80 px-3 py-1.5 rounded-lg text-xs">
            <span className="font-semibold text-slate-800">Campus Connect</span>
            <span className="text-slate-400">•</span>
            <span className="text-slate-600">Handover for <strong className="text-slate-800 font-medium">{project?.departing_member || 'Arjun Mehta'}</strong></span>
          </div>

          <div className={`px-2.5 py-1 rounded-full text-xs font-semibold ${currentStatus.bg} ${currentStatus.text}`}>
            {currentStatus.label}
          </div>
        </div>

        {/* Right: Segmented Role Selector + Reset Demo button */}
        <div className="flex items-center gap-3">
          {/* Role Segmented Control */}
          <div className="flex items-center bg-slate-100 border border-slate-200 p-1 rounded-xl">
            <span className="text-[11px] font-semibold text-slate-500 uppercase px-2 tracking-wider">
              Viewing As:
            </span>
            <div className="flex items-center gap-0.5">
              {rolesList.map((r) => {
                const cfg = ROLE_DETAILS[r];
                const isSelected = role === r;
                return (
                  <button
                    key={r}
                    onClick={() => setRole(r)}
                    title={`${cfg.label} (${cfg.name}): ${cfg.clearanceLabel}. ${cfg.description}`}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                      isSelected
                        ? 'bg-white text-navy font-semibold shadow-sm border border-slate-200/80'
                        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
                    }`}
                  >
                    <span>{cfg.label}</span>
                    <span
                      className={`ml-1.5 inline-block w-2 h-2 rounded-full ${
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

          {/* Reset Demo Button */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowResetModal(true)}
            leftIcon={<RefreshCw className="w-3.5 h-3.5 text-slate-500" />}
            title="Reset project data to clean empty state"
          >
            Reset demo
          </Button>
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
        <div className="p-2 flex items-start gap-3 text-slate-700 text-sm">
          <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
          <p>
            Are you sure you want to reset? You can re-populate synthetic demo data anytime by clicking <strong>&quot;Load demo project&quot;</strong> on the dashboard or sources page.
          </p>
        </div>
      </Modal>
    </header>
  );
};
