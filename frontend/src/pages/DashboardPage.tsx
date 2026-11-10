import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  CheckCircle,
  AlertTriangle,
  HelpCircle,
  Sparkles,
  ArrowRight,
  Play,
  FileSpreadsheet,
  Clock,
  Layers,
  Database,
  ShieldCheck,
  User,
  ShieldAlert,
} from 'lucide-react';
import { api } from '../api/client';
import { DashboardData } from '../types';
import { useRole } from '../context/RoleContext';
import { useToast } from '../context/ToastContext';
import { Card, CardHeader, CardTitle, CardContent } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Modal } from '../components/common/Modal';
import { ProgressRing } from '../components/common/ProgressRing';
import { EmptyState } from '../components/common/EmptyState';
import { Skeleton, CardSkeleton } from '../components/common/Skeleton';
import { StatusBadge, ClearanceBadge, ClaimTypeBadge } from '../components/common/Badge';

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { role, canLead, roleConfig } = useRole();
  const { success, error } = useToast();
  const queryClient = useQueryClient();
  const [showConfirmLoadDemo, setShowConfirmLoadDemo] = useState(false);

  const { data, isLoading } = useQuery<DashboardData>({
    queryKey: ['dashboard'],
    queryFn: api.getDashboard,
    staleTime: 5000,
  });

  const loadDemoMutation = useMutation({
    mutationFn: api.loadDemo,
    onSuccess: (res) => {
      queryClient.invalidateQueries();
      success('Demo Loaded', `Imported ${res.claims_count} factual claims from verified pipeline cache.`);
    },
    onError: (err: any) => error('Load Failed', err.message),
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-8 w-48 bg-slate-200 rounded animate-pulse" />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
        </div>
      </div>
    );
  }

  // 1. EMPTY STATE IF NO ANALYSIS / DATA
  if (!data?.has_analysis) {
    return (
      <div className="py-8">
        <EmptyState
          icon={<Database className="w-8 h-8 text-navy dark:text-teal" />}
          title="No Project Knowledge Extracted Yet"
          description="HandoverLedger reconstructs project state into verifiable claims from GitHub repos, meeting notes, and chat logs."
          actionText="Connect Sources"
          onAction={() => navigate('/sources')}
          actionIcon={<ArrowRight className="w-4 h-4" />}
          secondaryAction={
            canLead ? (
              <Button variant="outline" onClick={() => setShowConfirmLoadDemo(true)}>
                Load Demo Project
              </Button>
            ) : undefined
          }
        />

        {/* Confirm Load Demo Modal */}
        <Modal
          isOpen={showConfirmLoadDemo}
          onClose={() => setShowConfirmLoadDemo(false)}
          title="Load Synthetic Demo Project?"
          description="This will import the synthetic 'Campus Connect' demonstration dataset into your workspace."
          footer={
            <>
              <Button variant="outline" size="sm" onClick={() => setShowConfirmLoadDemo(false)}>
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                isLoading={loadDemoMutation.isPending}
                onClick={() => {
                  setShowConfirmLoadDemo(false);
                  loadDemoMutation.mutate();
                }}
              >
                Load Demo Project
              </Button>
            </>
          }
        >
          <div className="space-y-2 text-xs text-text-muted">
            <p>
              Are you sure you want to load synthetic demo data for <strong>Campus Connect</strong>?
            </p>
            <p>
              To work with your own repository or team notes instead, click <strong>Cancel</strong> and click <strong>Connect Sources</strong>.
            </p>
          </div>
        </Modal>
      </div>
    );
  }

  const { status_counts, readiness_percent, top_risks, next_actions, ownership_breakdown, recent_activity } = data;

  return (
    <div className="space-y-6">
      {/* Standard Page Header Pattern */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6">
        <div>
          <h2 className="page-title text-text-main">Project Overview</h2>
          <p className="text-sm text-text-muted mt-1">
            Real-time factual ledger state, verification metrics, and handover readiness.
          </p>
        </div>

        {/* Quick Action Buttons */}
        <div className="flex flex-wrap items-center gap-2 self-start sm:self-auto">
          {canLead && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate('/sources')}
              leftIcon={<Play className="w-3.5 h-3.5" />}
            >
              Run Analysis
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate('/ledger')}
            leftIcon={<FileSpreadsheet className="w-3.5 h-3.5" />}
          >
            Open Claim Ledger
          </Button>
          {(role === 'departing' || canLead) && (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => navigate('/interview')}
              leftIcon={<HelpCircle className="w-3.5 h-3.5" />}
            >
              Answer Questions
            </Button>
          )}
          {canLead && (
            <Button
              variant="primary"
              size="sm"
              onClick={() => navigate('/review')}
              rightIcon={<ArrowRight className="w-3.5 h-3.5" />}
            >
              Go to Review
            </Button>
          )}
        </div>
      </div>

      {/* Top Readiness & 4 Clickable Status Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* Readiness Progress Ring Card */}
        <Card className="flex flex-col items-center justify-center p-6 text-center sm:col-span-2 lg:col-span-1 bg-surface border-border shadow-soft">
          <ProgressRing progress={readiness_percent} size={90} strokeWidth={8} showPercent />
          <h4 className="text-sm font-semibold text-text-main mt-3">Readiness</h4>
          <p className="text-[11px] text-text-muted mt-0.5">
            {readiness_percent}% claims reviewed
          </p>
          <span className="mt-2 inline-block px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider bg-slate-100 dark:bg-slate-800 text-text-muted border border-border">
            {data.handover_status}
          </span>
        </Card>

        {/* 4 Clickable Status Cards */}
        {/* 1. Verified */}
        <Card
          hoverable
          onClick={() => navigate('/ledger?status=verified')}
          className="p-5 cursor-pointer border-l-4 border-l-status-verified-text bg-surface border-border shadow-soft"
        >
          <div className="flex justify-between items-start">
            <span className="text-xs font-semibold text-status-verified-text uppercase tracking-wider">
              Verified
            </span>
            <CheckCircle className="w-4 h-4 text-status-verified-text" />
          </div>
          <div className="text-3xl font-bold text-text-main mt-2">{status_counts.verified}</div>
          <p className="text-xs text-text-muted mt-1">Dual-check supported claims</p>
        </Card>

        {/* 2. Inferred */}
        <Card
          hoverable
          onClick={() => navigate('/ledger?status=inferred')}
          className="p-5 cursor-pointer border-l-4 border-l-status-inferred-text bg-surface border-border shadow-soft"
        >
          <div className="flex justify-between items-start">
            <span className="text-xs font-semibold text-status-inferred-text uppercase tracking-wider">
              Inferred
            </span>
            <Sparkles className="w-4 h-4 text-status-inferred-text" />
          </div>
          <div className="text-3xl font-bold text-text-main mt-2">{status_counts.inferred}</div>
          <p className="text-xs text-text-muted mt-1">Contextual / leaver-attested</p>
        </Card>

        {/* 3. Conflicting */}
        <Card
          hoverable
          onClick={() => navigate('/ledger?status=conflicting')}
          className="p-5 cursor-pointer border-l-4 border-l-status-conflicting-text bg-surface border-border shadow-soft"
        >
          <div className="flex justify-between items-start">
            <span className="text-xs font-semibold text-status-conflicting-text uppercase tracking-wider">
              Conflicting
            </span>
            <AlertTriangle className="w-4 h-4 text-status-conflicting-text" />
          </div>
          <div className="text-3xl font-bold text-text-main mt-2">{status_counts.conflicting}</div>
          <p className="text-xs text-text-muted mt-1">{data.open_conflicts_count} open conflict links</p>
        </Card>

        {/* 4. Missing */}
        <Card
          hoverable
          onClick={() => navigate('/ledger?status=missing')}
          className="p-5 cursor-pointer border-l-4 border-l-status-missing-text bg-surface border-border shadow-soft"
        >
          <div className="flex justify-between items-start">
            <span className="text-xs font-semibold text-status-missing-text uppercase tracking-wider">
              Missing
            </span>
            <HelpCircle className="w-4 h-4 text-status-missing-text" />
          </div>
          <div className="text-3xl font-bold text-text-main mt-2">{status_counts.missing}</div>
          <p className="text-xs text-text-muted mt-1">{data.unanswered_questions_count} unanswered questions</p>
        </Card>
      </div>

      {/* Main Dashboard Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column (2 cols): Top Risks & Next Actions */}
        <div className="lg:col-span-2 space-y-6">
          {/* Top Risks */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-text-main">
                <ShieldAlert className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                <span>Top Identified Risks ({top_risks.length})</span>
              </CardTitle>
              <Button variant="ghost" size="sm" onClick={() => navigate('/ledger?type=risk')}>
                View all risks
              </Button>
            </CardHeader>
            <CardContent className="divide-y divide-border p-0">
              {top_risks.length === 0 ? (
                <p className="text-xs text-text-muted p-5 italic">No open risk claims recorded.</p>
              ) : (
                top_risks.map((risk) => (
                  <div key={risk.id} className="p-4 hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition-colors flex items-start justify-between gap-4">
                    <div className="space-y-1">
                      <p className="text-sm font-medium text-text-main leading-snug">{risk.text}</p>
                      <div className="flex items-center gap-2 text-xs text-text-muted">
                        {risk.owner_name && <span>Owner: <strong className="text-text-main">{risk.owner_name}</strong></span>}
                        <span>•</span>
                        <span>Clearance: Level {risk.clearance}</span>
                      </div>
                    </div>
                    <div className="flex-shrink-0 flex items-center gap-2">
                      <StatusBadge status={risk.status} size="sm" />
                      <ClearanceBadge clearance={risk.clearance} size="sm" />
                    </div>
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          {/* Next Actions */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-text-main">
                <ArrowRight className="w-4 h-4 text-sky-600 dark:text-sky-400" />
                <span>Immediate Next Actions ({next_actions.length})</span>
              </CardTitle>
              <Button variant="ghost" size="sm" onClick={() => navigate('/ledger?type=next_action')}>
                View all actions
              </Button>
            </CardHeader>
            <CardContent className="divide-y divide-border p-0">
              {next_actions.length === 0 ? (
                <p className="text-xs text-text-muted p-5 italic">No next actions scheduled.</p>
              ) : (
                next_actions.map((act) => (
                  <div key={act.id} className="p-4 hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition-colors flex items-start justify-between gap-4">
                    <div className="space-y-1">
                      <p className="text-sm font-medium text-text-main leading-snug">{act.text}</p>
                      <div className="flex items-center gap-2 text-xs text-text-muted">
                        {act.owner_name && <span>Assignee: <strong className="text-text-main">{act.owner_name}</strong></span>}
                        {act.event_date && (
                          <>
                            <span>•</span>
                            <span>Target: {act.event_date}</span>
                          </>
                        )}
                      </div>
                    </div>
                    <div className="flex-shrink-0">
                      <StatusBadge status={act.status} size="sm" />
                    </div>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Column (1 col): Ownership Breakdown & Recent Activity */}
        <div className="space-y-6">
          {/* Ownership Breakdown */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-text-main">
                <User className="w-4 h-4 text-teal" />
                <span>Ownership Distribution</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {ownership_breakdown.length === 0 ? (
                <p className="text-xs text-text-muted italic">No ownership claims registered.</p>
              ) : (
                ownership_breakdown.map((item, idx) => {
                  const maxCount = Math.max(...ownership_breakdown.map((o) => o.count), 1);
                  const barWidth = Math.round((item.count / maxCount) * 100);
                  return (
                    <div key={idx} className="space-y-1">
                      <div className="flex justify-between text-xs">
                        <span className="font-semibold text-text-main">{item.owner_name}</span>
                        <span className="text-text-muted font-mono">{item.count} items</span>
                      </div>
                      <div className="w-full h-2 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-teal rounded-full transition-all duration-300"
                          style={{ width: `${barWidth}%` }}
                        />
                      </div>
                    </div>
                  );
                })
              )}
            </CardContent>
          </Card>

          {/* Recent Activity */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-text-main">
                <Clock className="w-4 h-4 text-text-muted" />
                <span>Recent Activity</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 p-4">
              {recent_activity.length === 0 ? (
                <p className="text-xs text-text-muted italic">No activity recorded yet.</p>
              ) : (
                recent_activity.slice(0, 5).map((act) => (
                  <div key={act.id} className="text-xs space-y-0.5 border-b border-border pb-2 last:border-0 last:pb-0">
                    <div className="flex justify-between items-center text-[11px] text-text-muted">
                      <span className="font-semibold text-text-main capitalize">{act.role}</span>
                      <span title={new Date(act.at).toLocaleString()}>
                        {new Date(act.at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                    <p className="text-text-muted line-clamp-1">{act.target}</p>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

