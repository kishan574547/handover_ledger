import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ShieldCheck,
  Download,
  Printer,
  CheckCircle2,
  Lock,
  AlertTriangle,
  FileText,
  User,
  Shield,
  Clock,
  Sparkles,
  ExternalLink,
  HelpCircle,
  X,
  Inbox,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { api } from '../api/client';
import { HandoverViewData, LeakCheckResult, DemoRole, CitationItem } from '../types';
import { useRole, ROLE_DETAILS } from '../context/RoleContext';
import { useToast } from '../context/ToastContext';
import { useProjectMeta } from '../context/ProjectMetaContext';
import { Card, CardHeader, CardTitle, CardContent } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Modal } from '../components/common/Modal';
import { Drawer } from '../components/common/Drawer';
import { StatusBadge, ClearanceBadge } from '../components/common/Badge';
import { TrustLens, TrustLensMode, filterClaimsByTrustLens } from '../components/common/TrustLens';
import { formatLocalDateTime } from '../utils/date';

export const HandoverPage: React.FC = () => {
  const navigate = useNavigate();
  const { role, canLead, canAcknowledge, roleConfig } = useRole();
  const { isDemo, displayName, leaverName } = useProjectMeta();
  const { success, error, warning } = useToast();
  const queryClient = useQueryClient();

  // Lead preview role selector
  const [previewRole, setPreviewRole] = useState<DemoRole>(role);
  const [trustMode, setTrustMode] = useState<TrustLensMode>('everything');
  const [isRecentChangesOpen, setIsRecentChangesOpen] = useState(false);

  // Modals & Drawers state
  const [isLeakCheckOpen, setIsLeakCheckOpen] = useState(false);
  const [leakCheckData, setLeakCheckData] = useState<LeakCheckResult | null>(null);
  const [isLeakCheckLoading, setIsLeakCheckLoading] = useState(false);

  const [isAckModalOpen, setIsAckModalOpen] = useState(false);
  const [ackName, setAckName] = useState(roleConfig.name);

  // Citation Popover state
  const [activeCitation, setActiveCitation] = useState<CitationItem | null>(null);

  // Fetch Handover View
  const effectiveRole = canLead ? previewRole : role;
  const { data: handover, isLoading, error: fetchError } = useQuery<HandoverViewData>({
    queryKey: ['handover-view', effectiveRole],
    queryFn: () => api.getHandoverView(canLead ? previewRole : undefined),
    retry: false,
  });

  // Acknowledgement mutation
  const acknowledgeMutation = useMutation({
    mutationFn: (name: string) => api.acknowledgeHandover(name),
    onSuccess: (ack) => {
      queryClient.invalidateQueries({ queryKey: ['handover-view'] });
      setIsAckModalOpen(false);
      success('Receipt Acknowledged', `${ack.name} confirmed receipt of this handover document.`);
    },
    onError: (err: any) => error('Acknowledgement Failed', err.message),
  });

  // Assign successor mutation
  const assignSuccessorMutation = useMutation({
    mutationFn: (claimId: string) => api.assignSuccessor(claimId),
    onSuccess: (data: any) => {
      queryClient.invalidateQueries({ queryKey: ['handover-view'] });
      success('Assigned to Successor', `Responsibility reassigned to ${data.owner_name}.`);
    },
    onError: (err: any) => error('Assignment Failed', err.message),
  });

  // Run Leak Check
  const handleRunLeakCheck = async () => {
    setIsLeakCheckLoading(true);
    setIsLeakCheckOpen(true);
    try {
      const res = await api.runLeakCheck(canLead ? previewRole : undefined);
      setLeakCheckData(res);
      if (res.passed) {
        success('Leak Check Passed', 'No higher-clearance claims or unmasked secrets detected.');
      } else {
        warning('Leak Findings Detected', `Found ${res.total_findings} security/clearance finding(s).`);
      }
    } catch (err: any) {
      error('Leak Check Failed', err.message);
    } finally {
      setIsLeakCheckLoading(false);
    }
  };

  // Export Markdown
  const handleExport = async () => {
    try {
      const markdown = await api.exportHandoverMarkdown(canLead ? previewRole : undefined);
      const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Handover_${effectiveRole}.md`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      success('Export Downloaded', `Generated clean Markdown export for ${effectiveRole}.`);
    } catch (err: any) {
      error('Export Blocked', err.message);
    }
  };

  // Print view
  const handlePrint = () => {
    window.print();
  };

  // 1. ROLE-AWARE UNAPPROVED STATE FOR NON-LEAD ROLES
  if (fetchError || (handover && handover.handover_status !== 'approved' && !canLead)) {
    return (
      <Card className="p-8 sm:p-12 text-center text-text-muted max-w-2xl mx-auto my-8 sm:my-12">
        <Clock className="w-12 h-12 text-amber-500 mx-auto mb-3" />
        <h3 className="text-lg font-bold text-text-main">
          The lead has not released the handover yet
        </h3>
        <p className="text-sm text-text-muted mt-2 max-w-md mx-auto leading-relaxed">
          {role === 'coordinator'
            ? `The Project Lead${isDemo ? ' (Priya Nair)' : ''} has not approved and released the handover yet. Once released, you will see general operational contacts, club decisions, and milestone records cleared for Level 1 (General).`
            : role === 'developer'
            ? `The Project Lead${isDemo ? ' (Priya Nair)' : ''} has not approved and released the handover yet. Once released, you will see full technical runbooks, architecture decisions, open tasks, and dependencies cleared up to Level 2 (Technical).`
            : 'The Project Lead is currently reviewing verified claims and resolving open conflicts. You can review current findings or answer open gap questions in the Exit Interview.'}
        </p>
        <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
          {role === 'departing' && (
            <Button variant="primary" onClick={() => window.location.href = '/interview'}>
              Go to Exit Interview
            </Button>
          )}
          <Button variant="outline" onClick={() => window.location.href = '/'}>
            Back to Dashboard
          </Button>
        </div>
      </Card>
    );
  }

  if (isLoading) {
    return <div className="p-12 text-center text-slate-400 animate-pulse">Loading handover ledger...</div>;
  }

  if (!handover) return null;

  const { sections, acknowledged, acknowledged_at, acknowledged_by } = handover;

  const renderEmptySection = (customMessage?: string) => (
    <div className="p-3 bg-slate-50/60 dark:bg-slate-900/40 rounded-card border border-dashed border-border-subtle flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 text-xs text-text-muted">
      <div className="flex items-center gap-2">
        <Inbox className="w-4 h-4 text-text-muted flex-shrink-0" />
        <span>{customMessage || 'Nothing found in the connected sources for this section.'}</span>
      </div>
      {canLead && (
        <button
          onClick={() => navigate('/sources')}
          className="text-[11px] text-navy dark:text-teal hover:underline font-semibold text-left sm:text-right flex-shrink-0"
        >
          Add meeting notes or a chat export to improve this section &rarr;
        </button>
      )}
    </div>
  );

  const renderCitationChip = (claimId: string) => {
    const cit = Object.values(sections || {})
      .flatMap((s: any) => s.citations || [])
      .find((c: any) => c.claim_id === claimId);
    return (
      <button
        key={claimId}
        type="button"
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          if (cit) setActiveCitation(cit);
        }}
        className="inline-flex items-center ml-1 px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold bg-navy/10 dark:bg-teal/20 text-navy dark:text-teal hover:bg-navy/20 dark:hover:bg-teal/30 transition-colors"
        title="View verifiable source quote"
      >
        [#{claimId.slice(0, 6)}]
      </button>
    );
  };

  return (
    <div className="space-y-6 pb-20">
      {/* Acknowledged Top Banner */}
      {handover.acknowledged_version_number && (handover.current_version_number ?? 1) > handover.acknowledged_version_number ? (
        <div className="p-4 bg-amber-50 border border-amber-200 rounded-card flex items-center justify-between shadow-sm">
          <div className="flex items-center gap-3">
            <Clock className="w-5 h-5 text-amber-600 flex-shrink-0" />
            <div className="text-xs">
              <span className="font-bold text-amber-950">Version {handover.acknowledged_version_number} was acknowledged</span>
              <span className="text-amber-800 ml-2">
                Confirmed by <strong>{acknowledged_by}</strong> on{' '}
                {acknowledged_at ? (
                  <span title={formatLocalDateTime(acknowledged_at).iso} className="cursor-help font-medium">
                    {formatLocalDateTime(acknowledged_at).display}
                  </span>
                ) : (
                  '—'
                )}
                ; <strong>Version {handover.current_version_number} is pending acknowledgement.</strong>
              </span>
            </div>
          </div>
          <span className="text-[11px] font-semibold text-amber-800 bg-amber-100 px-2 py-0.5 rounded">
            New Version Pending
          </span>
        </div>
      ) : acknowledged ? (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-card flex items-center justify-between shadow-sm">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />
            <div className="text-xs">
              <span className="font-bold text-emerald-950">
                Version {handover.acknowledged_version_number || 1} Acknowledged
              </span>
              <span className="text-emerald-800 ml-2">
                Confirmed by <strong>{acknowledged_by}</strong> on{' '}
                {acknowledged_at ? (
                  <span title={formatLocalDateTime(acknowledged_at).iso} className="cursor-help font-medium">
                    {formatLocalDateTime(acknowledged_at).display}
                  </span>
                ) : (
                  '—'
                )}
              </span>
            </div>
          </div>
          <span className="text-[11px] font-semibold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded">
            Official Audit Record
          </span>
        </div>
      ) : null}

      {/* Standard Page Header Pattern */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="page-title text-text-main">Project Handover Document</h2>
            <ClearanceBadge clearance={handover.clearance_level} size="sm" />
          </div>
          <p className="text-xs text-text-muted mt-1">
            Authoritative, citation-linked knowledge release for <strong>{effectiveRole.toUpperCase()}</strong> ({ROLE_DETAILS[effectiveRole as DemoRole]?.name}).
          </p>
        </div>

        {/* Lead Preview Selector & Actions */}
        <div className="flex flex-wrap items-center gap-2 self-start sm:self-auto">
          {canLead && (
            <div className="flex items-center gap-1 bg-surface border border-border px-2.5 py-1 rounded-btn text-xs min-h-[36px]">
              <span className="font-semibold text-text-muted uppercase text-[10px]">Preview As:</span>
              <select
                value={previewRole}
                onChange={(e) => setPreviewRole(e.target.value as DemoRole)}
                className="bg-transparent font-medium text-navy dark:text-teal focus:outline-none cursor-pointer"
                aria-label="Preview handover as role"
              >
                <option value="lead">Lead (Level 3 - Confidential)</option>
                <option value="developer">Developer (Level 2 - Technical)</option>
                <option value="coordinator">Coordinator (Level 1 - General)</option>
              </select>
            </div>
          )}

          <Button variant="outline" size="sm" onClick={handleRunLeakCheck} leftIcon={<Shield className="w-3.5 h-3.5" />}>
            Run Leak Check
          </Button>

          <Button variant="outline" size="sm" onClick={handleExport} leftIcon={<Download className="w-3.5 h-3.5" />}>
            Export Markdown
          </Button>

          <Button variant="outline" size="sm" onClick={handlePrint} leftIcon={<Printer className="w-3.5 h-3.5" />}>
            Print / PDF
          </Button>

          {canAcknowledge && !acknowledged && (
            <Button
              variant="accent"
              size="sm"
              onClick={() => setIsAckModalOpen(true)}
              leftIcon={<CheckCircle2 className="w-3.5 h-3.5" />}
            >
              Acknowledge Receipt
            </Button>
          )}
        </div>
      </div>

      {/* Trust Lens */}
      <TrustLens
        mode={trustMode}
        onChange={setTrustMode}
        totalCount={Object.values(sections || {}).flatMap((s: any) => s.claims || []).length}
        filteredCount={
          filterClaimsByTrustLens(
            Object.values(sections || {}).flatMap((s: any) => s.claims || []),
            trustMode
          ).length
        }
        className="no-print"
      />

      {/* Printable Document Container */}
      <div className="space-y-6">
        {/* Section 1: Project Snapshot */}
        <Card className="card">
          <CardHeader>
            <CardTitle className="text-base font-bold text-text-main">1. Project Snapshot & Overview</CardTitle>
            {sections.snapshot?.hidden_count > 0 && (
              <span className="text-xs text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200 font-medium flex items-center gap-1">
                <Lock className="w-3 h-3" />
                <span>{sections.snapshot.hidden_count} items hidden: you are not cleared to see them</span>
              </span>
            )}
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 p-3 bg-slate-50 dark:bg-slate-900/60 rounded-lg text-xs">
              <div>
                <span className="text-text-muted block">Project:</span>
                <strong className="text-text-main text-sm">{handover.project_name}</strong>
              </div>
              <div>
                <span className="text-text-muted block">Departing Member:</span>
                <strong className="text-text-main">{handover.departing_member}</strong>
              </div>
              <div>
                <span className="text-text-muted block">Successor:</span>
                <strong className="text-text-main">{handover.successor_name}</strong>
              </div>
              <div>
                <span className="text-text-muted block">Clearance Level:</span>
                <strong className="text-text-main">Level {handover.clearance_level}</strong>
              </div>
            </div>

            {(!sections.snapshot?.claims || sections.snapshot.claims.length === 0) ? (
              renderEmptySection()
            ) : (
              <div className="space-y-2 pt-2">
                {sections.snapshot.claims.map((claim) => (
                  <div key={claim.id} className="text-sm text-text-main leading-relaxed flex items-start justify-between gap-2">
                    <div className="flex items-start gap-2">
                      <span className="text-text-muted font-mono text-xs">•</span>
                      <p className="flex-1">
                        {claim.text}
                        {renderCitationChip(claim.id)}
                      </p>
                    </div>
                    <StatusBadge status={claim.status} isLeaverAttested={claim.created_by === 'leaver'} size="sm" />
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Section 2: Ownership Table */}
        <Card className="card">
          <CardHeader>
            <CardTitle className="text-base font-bold text-text-main">2. Ownership & Primary Responsibilities</CardTitle>
            {sections.ownership?.hidden_count > 0 && (
              <span className="text-xs text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200 font-medium flex items-center gap-1">
                <Lock className="w-3 h-3" />
                <span>{sections.ownership.hidden_count} items hidden</span>
              </span>
            )}
          </CardHeader>
          <CardContent className="p-0 overflow-x-auto">
            {(!sections.ownership?.claims || sections.ownership.claims.length === 0) ? (
              <div className="p-4">{renderEmptySection()}</div>
            ) : (
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-slate-50 dark:bg-slate-900/60 border-b border-border text-text-muted font-semibold uppercase">
                    <th className="py-2.5 px-4">Subject / Domain</th>
                    <th className="py-2.5 px-4">Owner / Assignee</th>
                    <th className="py-2.5 px-4">Claim Statement</th>
                    <th className="py-2.5 px-4">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {sections.ownership.claims.map((claim) => {
                    const isUnassigned = !claim.owner_name || claim.owner_name.toLowerCase() === 'unassigned';
                    return (
                      <tr key={claim.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40">
                        <td className="py-2.5 px-4 font-semibold text-text-main capitalize font-mono">
                          {claim.subject_key.replace(/_/g, ' ')}
                        </td>
                        <td className="py-2.5 px-4 font-medium text-navy dark:text-teal">
                          <div className="flex items-center gap-2">
                            <span>{claim.owner_name || 'Unassigned'}</span>
                            {isUnassigned && canLead && (
                              <button
                                type="button"
                                onClick={() => assignSuccessorMutation.mutate(claim.id)}
                                disabled={assignSuccessorMutation.isPending}
                                className="px-1.5 py-0.5 text-[10px] rounded bg-navy text-white hover:bg-navy-light font-sans font-semibold transition-colors disabled:opacity-50"
                                title={`Assign this unassigned item to successor (${handover.successor_name})`}
                              >
                                Assign Successor
                              </button>
                            )}
                          </div>
                        </td>
                        <td className="py-2.5 px-4 text-text-main">
                          {claim.text}
                          {renderCitationChip(claim.id)}
                        </td>
                        <td className="py-2.5 px-4">
                          <StatusBadge status={claim.status} isLeaverAttested={claim.created_by === 'leaver'} size="sm" />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>

        {/* Section 3: Key Decisions with Rationale */}
        <Card className="card">
          <CardHeader>
            <CardTitle className="text-base font-bold text-text-main">3. Key Decisions & Technical Rationale</CardTitle>
            {sections.decisions?.hidden_count > 0 && (
              <span className="text-xs text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200 font-medium flex items-center gap-1">
                <Lock className="w-3 h-3" />
                <span>{sections.decisions.hidden_count} items hidden</span>
              </span>
            )}
          </CardHeader>
          <CardContent className="space-y-3">
            {(!sections.decisions?.claims || sections.decisions.claims.length === 0) ? (
              renderEmptySection()
            ) : (
              sections.decisions.claims.map((claim) => (
                <div key={claim.id} className="p-3 bg-slate-50/70 dark:bg-slate-900/40 rounded-lg border border-border space-y-1">
                  <div className="flex justify-between items-start gap-2">
                    <p className="text-sm font-semibold text-text-main">
                      {claim.text}
                      {renderCitationChip(claim.id)}
                    </p>
                    <StatusBadge status={claim.status} isLeaverAttested={claim.created_by === 'leaver'} size="sm" />
                  </div>
                  {claim.event_date && (
                    <span className="text-[11px] text-text-muted font-mono">Recorded: {claim.event_date}</span>
                  )}
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {/* Section 4: Open Work and Blockers */}
        <Card className="card">
          <CardHeader>
            <CardTitle className="text-base font-bold text-text-main">4. Open Work & Active Blockers</CardTitle>
            {sections.open_work?.hidden_count > 0 && (
              <span className="text-xs text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200 font-medium flex items-center gap-1">
                <Lock className="w-3 h-3" />
                <span>{sections.open_work.hidden_count} items hidden</span>
              </span>
            )}
          </CardHeader>
          <CardContent className="space-y-2">
            {(!sections.open_work?.claims || sections.open_work.claims.length === 0) ? (
              renderEmptySection()
            ) : (
              sections.open_work.claims.map((claim) => (
                <div key={claim.id} className="p-3 rounded-lg border border-border flex items-start justify-between gap-3 bg-surface">
                  <div>
                    <p className="text-sm font-medium text-text-main">
                      {claim.text}
                      {renderCitationChip(claim.id)}
                    </p>
                    <span className="text-xs text-text-muted font-medium">Assignee: {claim.owner_name || 'Unassigned'}</span>
                  </div>
                  <StatusBadge status={claim.status} isLeaverAttested={claim.created_by === 'leaver'} size="sm" />
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {/* Section 5: Risks */}
        <Card className="card">
          <CardHeader>
            <CardTitle className="text-base font-bold text-text-main">5. Operational & Technical Risks</CardTitle>
            {sections.risks?.hidden_count > 0 && (
              <span className="text-xs text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200 font-medium flex items-center gap-1">
                <Lock className="w-3 h-3" />
                <span>{sections.risks.hidden_count} items hidden</span>
              </span>
            )}
          </CardHeader>
          <CardContent className="space-y-2">
            {(!sections.risks?.claims || sections.risks.claims.length === 0) ? (
              renderEmptySection()
            ) : (
              sections.risks.claims.map((claim) => (
                <div key={claim.id} className="p-3 bg-rose-50/40 dark:bg-rose-950/20 rounded-lg border border-rose-200 dark:border-rose-900 text-xs text-rose-950 dark:text-rose-200 font-medium flex justify-between items-center gap-3">
                  <div>
                    <span>{claim.text}</span>
                    {renderCitationChip(claim.id)}
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <ClearanceBadge clearance={claim.clearance} size="sm" />
                    <StatusBadge status={claim.status} isLeaverAttested={claim.created_by === 'leaver'} size="sm" />
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {/* Section 6: Dependencies & Integrations */}
        <Card className="card">
          <CardHeader>
            <CardTitle className="text-base font-bold text-text-main">6. Third-Party Dependencies & Integrations</CardTitle>
            {sections.dependencies?.hidden_count > 0 && (
              <span className="text-xs text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200 font-medium flex items-center gap-1">
                <Lock className="w-3 h-3" />
                <span>{sections.dependencies.hidden_count} items hidden</span>
              </span>
            )}
          </CardHeader>
          <CardContent className="space-y-2">
            {(!sections.dependencies?.claims || sections.dependencies.claims.length === 0) ? (
              renderEmptySection()
            ) : (
              sections.dependencies.claims.map((claim) => (
                <div key={claim.id} className="p-3 bg-slate-50 dark:bg-slate-900/40 rounded-lg border border-border text-xs text-text-main flex items-center justify-between gap-3">
                  <div>
                    <span>{claim.text}</span>
                    {renderCitationChip(claim.id)}
                  </div>
                  <StatusBadge status={claim.status} isLeaverAttested={claim.created_by === 'leaver'} size="sm" />
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {/* Section 7: Contacts */}
        <Card className="card">
          <CardHeader>
            <CardTitle className="text-base font-bold text-text-main">7. Key Stakeholder & Escalation Contacts</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {(!sections.contacts?.claims || sections.contacts.claims.length === 0) ? (
              renderEmptySection()
            ) : (
              sections.contacts.claims.map((claim) => (
                <div key={claim.id} className="p-3 rounded-lg border border-border text-xs flex justify-between items-center gap-3">
                  <div>
                    <span className="font-semibold text-text-main">{claim.text}</span>
                    {renderCitationChip(claim.id)}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-text-muted">{claim.owner_name}</span>
                    <StatusBadge status={claim.status} isLeaverAttested={claim.created_by === 'leaver'} size="sm" />
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {/* Section 8: Recurring Problems */}
        <Card className="card">
          <CardHeader>
            <CardTitle className="text-base font-bold text-text-main">8. Recurring Problems & Mitigations</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {(!sections.recurring_problems?.claims || sections.recurring_problems.claims.length === 0) ? (
              renderEmptySection()
            ) : (
              sections.recurring_problems.claims.map((claim) => (
                <div key={claim.id} className="p-3 bg-amber-50/50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-900 rounded-lg text-xs text-amber-950 dark:text-amber-200 flex items-center justify-between gap-3">
                  <div>
                    <span>{claim.text}</span>
                    {renderCitationChip(claim.id)}
                  </div>
                  <StatusBadge status={claim.status} isLeaverAttested={claim.created_by === 'leaver'} size="sm" />
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {/* Section 9: Next Actions */}
        <Card className="card">
          <CardHeader>
            <CardTitle className="text-base font-bold text-text-main">9. Immediate Next Actions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {(!sections.next_actions?.claims || sections.next_actions.claims.length === 0) ? (
              renderEmptySection('No next actions found in the sources.')
            ) : (
              sections.next_actions.claims.map((claim) => (
                <div key={claim.id} className="p-3 border border-border rounded-lg text-xs text-text-main font-medium flex items-center justify-between gap-3 bg-surface">
                  <div>
                    <span>{claim.text}</span>
                    {renderCitationChip(claim.id)}
                    {claim.owner_name && (
                      <span className="text-[11px] text-text-muted ml-2">Assignee: {claim.owner_name}</span>
                    )}
                  </div>
                  <StatusBadge status={claim.status} isLeaverAttested={claim.created_by === 'leaver'} size="sm" />
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {/* Recent Changes (Collapsible) */}
        <Card className="card">
          <CardHeader className="cursor-pointer select-none" onClick={() => setIsRecentChangesOpen(!isRecentChangesOpen)}>
            <div className="flex items-center justify-between w-full">
              <div className="flex items-center gap-2">
                <CardTitle className="text-base font-bold text-text-main">Recent Changes</CardTitle>
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-text-muted">
                  {sections.recent_changes?.claims?.length || 0}
                </span>
              </div>
              <button type="button" className="text-text-muted hover:text-text-main p-1" aria-label="Toggle recent changes">
                {isRecentChangesOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </button>
            </div>
          </CardHeader>
          {isRecentChangesOpen && (
            <CardContent className="space-y-2 pt-0">
              {(!sections.recent_changes?.claims || sections.recent_changes.claims.length === 0) ? (
                renderEmptySection()
              ) : (
                sections.recent_changes.claims.slice(0, 15).map((claim) => (
                  <div key={claim.id} className="p-2.5 rounded-lg border border-border bg-surface flex items-start justify-between gap-3 text-xs">
                    <div className="flex-1">
                      <span className="text-text-main">{claim.text}</span>
                      {renderCitationChip(claim.id)}
                    </div>
                    <StatusBadge status={claim.status} isLeaverAttested={claim.created_by === 'leaver'} size="sm" />
                  </div>
                ))
              )}
            </CardContent>
          )}
        </Card>

        {/* Section 10: First-Week Plan */}
        <Card className="card">
          <CardHeader>
            <CardTitle className="text-base font-bold text-text-main">10. First-Week Onboarding Checklist</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {isDemo ? (
              <>
                <div className="space-y-2">
                  <h4 className="text-xs font-bold text-navy dark:text-teal uppercase tracking-wider">Days 1 - 2: Access & Local Environment</h4>
                  <div className="space-y-1.5 pl-2">
                    {[
                      'Clone repository and configure local backend with SQLite',
                      'Verify GitHub permissions and branch protection rules',
                      'Confirm campus SSO staging authentication domain',
                    ].map((item, idx) => (
                      <label key={idx} className="flex items-center gap-2 text-xs text-text-main cursor-pointer">
                        <input type="checkbox" className="rounded border-slate-300 text-navy focus:ring-navy" />
                        <span>{item}</span>
                      </label>
                    ))}
                  </div>
                </div>

                <div className="space-y-2 pt-2 border-t border-border">
                  <h4 className="text-xs font-bold text-navy dark:text-teal uppercase tracking-wider">Days 3 - 5: Architecture Shadowing & Releases</h4>
                  <div className="space-y-1.5 pl-2">
                    {[
                      'Run end-to-end integration test on local Docker compose',
                      'Meet with Mr. Kapoor regarding hostel network port forwarding',
                      'Review unowned PR #9 (Notification service queue) and assign successor',
                    ].map((item, idx) => (
                      <label key={idx} className="flex items-center gap-2 text-xs text-text-main cursor-pointer">
                        <input type="checkbox" className="rounded border-slate-300 text-navy focus:ring-navy" />
                        <span>{item}</span>
                      </label>
                    ))}
                  </div>
                </div>
              </>
            ) : (!sections.first_week_plan?.claims || sections.first_week_plan.claims.length === 0) ? (
              <div className="p-4 bg-slate-50/60 dark:bg-slate-900/40 rounded-card border border-dashed border-border-subtle space-y-3">
                <div className="flex items-center gap-2 text-xs text-text-muted font-semibold">
                  <Inbox className="w-4 h-4 text-text-muted" />
                  <span>Not enough approved material to build a first-week plan yet</span>
                </div>
                <p className="text-xs text-text-muted">
                  To generate an automated, cited first-week onboarding plan, ensure your project has approved claims under:
                </p>
                <ul className="list-disc list-inside text-xs text-text-muted space-y-1 pl-2">
                  <li>Next actions and TODO items</li>
                  <li>Open work and active PRs/issues</li>
                  <li>Operational and technical risks</li>
                  <li>Component ownership & responsibilities</li>
                  <li>External dependencies & environment configurations</li>
                </ul>
                {canLead && (
                  <Button variant="outline" size="sm" onClick={() => navigate('/review')} className="mt-2">
                    Go to Review Ledger &rarr;
                  </Button>
                )}
              </div>
            ) : (
              <div className="space-y-4">
                {/* Days 1 - 2 */}
                <div className="space-y-2">
                  <h4 className="text-xs font-bold text-navy dark:text-teal uppercase tracking-wider">Days 1 - 2: Access & Environment Foundations</h4>
                  <div className="space-y-2 pl-2">
                    {sections.first_week_plan.claims.slice(0, Math.ceil(sections.first_week_plan.claims.length / 2)).map((claim) => (
                      <label key={claim.id} className="flex items-start gap-2.5 text-xs text-text-main cursor-pointer p-2 rounded hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors">
                        <input type="checkbox" className="mt-0.5 rounded border-slate-300 text-navy focus:ring-navy" />
                        <div className="flex-1 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
                          <div>
                            <span>{claim.text}</span>
                            {renderCitationChip(claim.id)}
                            {claim.owner_name && (
                              <span className="text-[11px] text-text-muted ml-2">({claim.owner_name})</span>
                            )}
                          </div>
                          <StatusBadge status={claim.status} isLeaverAttested={claim.created_by === 'leaver'} size="sm" />
                        </div>
                      </label>
                    ))}
                  </div>
                </div>

                {/* Days 3 - 5 */}
                {sections.first_week_plan.claims.length > 1 && (
                  <div className="space-y-2 pt-2 border-t border-border">
                    <h4 className="text-xs font-bold text-navy dark:text-teal uppercase tracking-wider">Days 3 - 5: Architecture Deep Dive & Open Work</h4>
                    <div className="space-y-2 pl-2">
                      {sections.first_week_plan.claims.slice(Math.ceil(sections.first_week_plan.claims.length / 2)).map((claim) => (
                        <label key={claim.id} className="flex items-start gap-2.5 text-xs text-text-main cursor-pointer p-2 rounded hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors">
                          <input type="checkbox" className="mt-0.5 rounded border-slate-300 text-navy focus:ring-navy" />
                          <div className="flex-1 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
                            <div>
                              <span>{claim.text}</span>
                              {renderCitationChip(claim.id)}
                              {claim.owner_name && (
                                <span className="text-[11px] text-text-muted ml-2">({claim.owner_name})</span>
                              )}
                            </div>
                            <StatusBadge status={claim.status} isLeaverAttested={claim.created_by === 'leaver'} size="sm" />
                          </div>
                        </label>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Section 11: Unresolved and Uncertain (in amber) */}
        <Card className="card border-amber-300 bg-amber-50/20">
          <CardHeader>
            <CardTitle className="text-base font-bold text-amber-900 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-600" />
              <span>11. Unresolved Items & Operational Uncertainties</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-xs text-amber-800">
              These items represent conflicts, missing documentation, or unverified leaver attestations that require ongoing attention.
            </p>
            {(!sections.unresolved?.claims || sections.unresolved.claims.length === 0) ? (
              renderEmptySection('No unresolved items or ambiguities flagged for this role.')
            ) : (
              sections.unresolved.claims.map((claim) => (
                <div key={claim.id} className="p-3 bg-surface rounded-lg border border-amber-200 shadow-xs flex justify-between items-start gap-3">
                  <div>
                    <p className="text-xs font-semibold text-text-main">
                      {claim.text}
                      {renderCitationChip(claim.id)}
                    </p>
                    <span className="text-[11px] text-text-muted font-mono mt-0.5 block">
                      Subject: {claim.subject_key}
                    </span>
                  </div>
                  <StatusBadge status={claim.status} isLeaverAttested={claim.created_by === 'leaver'} size="sm" />
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>

      {/* Leak Check Drawer */}
      <Drawer
        isOpen={isLeakCheckOpen}
        onClose={() => setIsLeakCheckOpen(false)}
        title="Handover Security Leak Check"
        subtitle={`Role: ${effectiveRole.toUpperCase()} • Max Clearance: Level ${handover.clearance_level}`}
      >
        <div className="space-y-4">
          {isLeakCheckLoading ? (
            <div className="p-8 text-center text-slate-400">Scanning view for clearance violations and unmasked secrets...</div>
          ) : leakCheckData ? (
            <div className="space-y-4">
              <div
                className={`p-4 rounded-xl border flex items-center gap-3 ${
                  leakCheckData.passed
                    ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
                    : 'bg-rose-50 border-rose-200 text-rose-900'
                }`}
              >
                {leakCheckData.passed ? (
                  <CheckCircle2 className="w-6 h-6 text-emerald-600 flex-shrink-0" />
                ) : (
                  <AlertTriangle className="w-6 h-6 text-rose-600 flex-shrink-0" />
                )}
                <div>
                  <h4 className="font-bold text-sm">
                    {leakCheckData.passed ? 'Leak Check Passed Cleanly' : 'Security Leak Check Failed'}
                  </h4>
                  <p className="text-xs mt-0.5">
                    {leakCheckData.passed
                      ? 'No higher clearance claims, raw passwords, API keys, or unmasked PII found.'
                      : `Identified ${leakCheckData.total_findings} security finding(s) that must be resolved before export.`}
                  </p>
                </div>
              </div>

              {!leakCheckData.passed && (
                <div className="space-y-2">
                  <h4 className="text-xs font-semibold text-slate-700 uppercase">Findings:</h4>
                  {leakCheckData.findings.map((f, i) => (
                    <div key={i} className="p-3 bg-rose-50/70 border border-rose-200 rounded-lg text-xs text-rose-900 font-mono">
                      {f}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : null}
        </div>
      </Drawer>

      {/* Acknowledge Receipt Modal */}
      <Modal
        isOpen={isAckModalOpen}
        onClose={() => setIsAckModalOpen(false)}
        title="Acknowledge Receipt of Project Handover"
        description="Formal signoff confirming you have reviewed the verified handover ledger for this role."
        footer={
          <>
            <Button variant="outline" size="sm" onClick={() => setIsAckModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="accent"
              size="sm"
              isLoading={acknowledgeMutation.isPending}
              onClick={() => ackName.trim() && acknowledgeMutation.mutate(ackName.trim())}
            >
              Sign and Confirm Receipt
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <label className="text-xs font-semibold text-slate-700 block">Your Full Name & Role</label>
          <input
            type="text"
            value={ackName}
            onChange={(e) => setAckName(e.target.value)}
            className="w-full text-xs p-3 border border-slate-300 rounded-lg focus:ring-1 focus:ring-navy focus:outline-none"
          />
          <p className="text-[11px] text-slate-500">
            By acknowledging, you confirm you have received the handover ledger for <strong>{effectiveRole}</strong>.
          </p>
        </div>
      </Modal>

      {/* Citation Popover Modal */}
      <Modal
        isOpen={!!activeCitation}
        onClose={() => setActiveCitation(null)}
        title="Verifiable Citation Evidence"
        description="Passage from project records evidencing this claim statement."
      >
        {activeCitation && (
          <div className="space-y-3 text-xs">
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
              <span className="font-semibold text-slate-800 block mb-1">Claim Statement:</span>
              <p className="text-slate-900">{activeCitation.text}</p>
            </div>

            <div className="p-3 bg-white rounded-lg border border-slate-200 font-mono text-slate-800">
              <span className="text-[10px] text-slate-400 block uppercase font-sans mb-1">
                Source: {activeCitation.source_name || 'Project Source'} • {activeCitation.location_label || 'Location'}
              </span>
              <div className="p-2 bg-amber-50 rounded border border-amber-200/80 text-amber-950 font-semibold">
                &quot;{activeCitation.quote}&quot;
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};
