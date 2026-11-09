import React, { useState } from 'react';
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
} from 'lucide-react';
import { api } from '../api/client';
import { HandoverViewData, LeakCheckResult, DemoRole, CitationItem } from '../types';
import { useRole, ROLE_DETAILS } from '../context/RoleContext';
import { useToast } from '../context/ToastContext';
import { Card, CardHeader, CardTitle, CardContent } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Modal } from '../components/common/Modal';
import { Drawer } from '../components/common/Drawer';
import { StatusBadge, ClearanceBadge } from '../components/common/Badge';
import { TrustLens, TrustLensMode, filterClaimsByTrustLens } from '../components/common/TrustLens';

export const HandoverPage: React.FC = () => {
  const { role, canLead, canAcknowledge, roleConfig } = useRole();
  const { success, error, warning } = useToast();
  const queryClient = useQueryClient();

  // Lead preview role selector
  const [previewRole, setPreviewRole] = useState<DemoRole>(role);
  const [trustMode, setTrustMode] = useState<TrustLensMode>('everything');

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
            ? 'The Project Lead (Priya Nair) has not approved and released the handover yet. Once released, you will see general operational contacts, club decisions, and milestone records cleared for Level 1 (General).'
            : role === 'developer'
            ? 'The Project Lead (Priya Nair) has not approved and released the handover yet. Once released, you will see full technical runbooks, architecture decisions, open tasks, and dependencies cleared up to Level 2 (Technical).'
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

  return (
    <div className="space-y-6 pb-20">
      {/* Acknowledged Top Banner */}
      {acknowledged && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-card flex items-center justify-between shadow-sm">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />
            <div className="text-xs">
              <span className="font-bold text-emerald-950">Receipt Acknowledged</span>
              <span className="text-emerald-800 ml-2">
                Confirmed by <strong>{acknowledged_by}</strong> on {acknowledged_at && new Date(acknowledged_at).toLocaleString()}
              </span>
            </div>
          </div>
          <span className="text-[11px] font-semibold text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded">
            Official Audit Record
          </span>
        </div>
      )}

      {/* Handover Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Project Handover Document</h2>
            <ClearanceBadge clearance={handover.clearance_level} size="sm" />
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Authoritative, citation-linked knowledge release for <strong>{effectiveRole.toUpperCase()}</strong> ({ROLE_DETAILS[effectiveRole as DemoRole]?.name}).
          </p>
        </div>

        {/* Lead Preview Selector & Actions */}
        <div className="flex flex-wrap items-center gap-2">
          {canLead && (
            <div className="flex items-center gap-1 bg-white border border-slate-200 px-2.5 py-1 rounded-lg text-xs">
              <span className="font-semibold text-slate-500 uppercase text-[10px]">Preview As:</span>
              <select
                value={previewRole}
                onChange={(e) => setPreviewRole(e.target.value as DemoRole)}
                className="bg-transparent font-medium text-navy focus:outline-none cursor-pointer"
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
            <CardTitle className="text-base font-bold text-slate-900">1. Project Snapshot & Overview</CardTitle>
            {sections.snapshot?.hidden_count > 0 && (
              <span className="text-xs text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200 font-medium flex items-center gap-1">
                <Lock className="w-3 h-3" />
                <span>{sections.snapshot.hidden_count} items hidden: you are not cleared to see them</span>
              </span>
            )}
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 p-3 bg-slate-50 rounded-lg text-xs">
              <div>
                <span className="text-slate-500 block">Project:</span>
                <strong className="text-slate-900 text-sm">{handover.project_name}</strong>
              </div>
              <div>
                <span className="text-slate-500 block">Departing Member:</span>
                <strong className="text-slate-900">{handover.departing_member}</strong>
              </div>
              <div>
                <span className="text-slate-500 block">Successor:</span>
                <strong className="text-slate-900">{handover.successor_name}</strong>
              </div>
              <div>
                <span className="text-slate-500 block">Clearance Level:</span>
                <strong className="text-slate-900">Level {handover.clearance_level}</strong>
              </div>
            </div>

            <div className="space-y-2 pt-2">
              {sections.snapshot?.claims.map((claim, idx) => (
                <div key={claim.id} className="text-sm text-slate-800 leading-relaxed flex items-start gap-2">
                  <span className="text-slate-400 font-mono text-xs">•</span>
                  <p className="flex-1">
                    {claim.text}
                    {/* Clickable Citation Chip */}
                    <button
                      onClick={() => {
                        const cit = sections.snapshot.citations.find((c) => c.claim_id === claim.id);
                        if (cit) setActiveCitation(cit);
                      }}
                      className="inline-flex items-center ml-1.5 px-1.5 py-0.2 rounded text-[11px] font-mono font-semibold bg-navy/10 text-navy hover:bg-navy hover:text-white transition-colors"
                      title="View verifiable source quote"
                    >
                      [{idx + 1}]
                    </button>
                  </p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Section 2: Ownership Table */}
        <Card className="card">
          <CardHeader>
            <CardTitle className="text-base font-bold text-slate-900">2. Ownership & Primary Responsibilities</CardTitle>
            {sections.ownership?.hidden_count > 0 && (
              <span className="text-xs text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200 font-medium flex items-center gap-1">
                <Lock className="w-3 h-3" />
                <span>{sections.ownership.hidden_count} items hidden</span>
              </span>
            )}
          </CardHeader>
          <CardContent className="p-0 overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase">
                  <th className="py-2.5 px-4">Subject / Domain</th>
                  <th className="py-2.5 px-4">Owner / Assignee</th>
                  <th className="py-2.5 px-4">Claim Statement</th>
                  <th className="py-2.5 px-4">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {sections.ownership?.claims.map((claim) => (
                  <tr key={claim.id}>
                    <td className="py-2.5 px-4 font-semibold text-slate-800 capitalize font-mono">
                      {claim.subject_key.replace(/_/g, ' ')}
                    </td>
                    <td className="py-2.5 px-4 font-medium text-navy">{claim.owner_name || 'Unassigned'}</td>
                    <td className="py-2.5 px-4 text-slate-700">{claim.text}</td>
                    <td className="py-2.5 px-4">
                      <StatusBadge status={claim.status} size="sm" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>

        {/* Section 3: Key Decisions with Rationale */}
        <Card className="card">
          <CardHeader>
            <CardTitle className="text-base font-bold text-slate-900">3. Key Decisions & Technical Rationale</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {sections.decisions?.claims.map((claim) => (
              <div key={claim.id} className="p-3 bg-slate-50/70 rounded-lg border border-slate-200/80 space-y-1">
                <div className="flex justify-between items-start">
                  <p className="text-sm font-semibold text-slate-900">{claim.text}</p>
                  <StatusBadge status={claim.status} size="sm" />
                </div>
                {claim.event_date && (
                  <span className="text-[11px] text-slate-400 font-mono">Recorded: {claim.event_date}</span>
                )}
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Section 4: Open Work and Blockers */}
        <Card className="card">
          <CardHeader>
            <CardTitle className="text-base font-bold text-slate-900">4. Open Work & Active Blockers</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {sections.open_work?.claims.map((claim) => (
              <div key={claim.id} className="p-3 rounded-lg border border-slate-200 flex items-start justify-between gap-3 bg-white">
                <div>
                  <p className="text-sm font-medium text-slate-900">{claim.text}</p>
                  <span className="text-xs text-slate-500 font-medium">Assignee: {claim.owner_name || 'Unassigned'}</span>
                </div>
                <StatusBadge status={claim.status} size="sm" />
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Section 5: Risks */}
        <Card className="card">
          <CardHeader>
            <CardTitle className="text-base font-bold text-slate-900">5. Operational & Technical Risks</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {sections.risks?.claims.map((claim) => (
              <div key={claim.id} className="p-3 bg-rose-50/40 rounded-lg border border-rose-200 text-xs text-rose-950 font-medium flex justify-between items-center">
                <span>{claim.text}</span>
                <ClearanceBadge clearance={claim.clearance} size="sm" />
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Section 6: Dependencies & Integrations */}
        <Card className="card">
          <CardHeader>
            <CardTitle className="text-base font-bold text-slate-900">6. Third-Party Dependencies & Integrations</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {sections.dependencies?.claims.map((claim) => (
              <div key={claim.id} className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs text-slate-800">
                {claim.text}
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Section 7: Contacts */}
        <Card className="card">
          <CardHeader>
            <CardTitle className="text-base font-bold text-slate-900">7. Key Stakeholder & Escalation Contacts</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {sections.contacts?.claims.map((claim) => (
              <div key={claim.id} className="p-3 rounded-lg border border-slate-200 text-xs flex justify-between items-center">
                <span className="font-semibold text-slate-800">{claim.text}</span>
                <span className="font-mono text-slate-500">{claim.owner_name}</span>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Section 8: Recurring Problems */}
        <Card className="card">
          <CardHeader>
            <CardTitle className="text-base font-bold text-slate-900">8. Recurring Problems & Mitigations</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {sections.recurring_problems?.claims.map((claim) => (
              <div key={claim.id} className="p-3 bg-amber-50/50 border border-amber-200 rounded-lg text-xs text-amber-950">
                {claim.text}
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Section 9: Next Actions */}
        <Card className="card">
          <CardHeader>
            <CardTitle className="text-base font-bold text-slate-900">9. Immediate Next Actions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {sections.next_actions?.claims.map((claim) => (
              <div key={claim.id} className="p-3 border border-slate-200 rounded-lg text-xs text-slate-800 font-medium">
                {claim.text}
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Section 10: First-Week Plan (Checklist with checkboxes) */}
        <Card className="card">
          <CardHeader>
            <CardTitle className="text-base font-bold text-slate-900">10. First-Week Onboarding Checklist</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <h4 className="text-xs font-bold text-navy uppercase tracking-wider">Days 1 - 2: Access & Local Environment</h4>
              <div className="space-y-1.5 pl-2">
                {[
                  'Clone repository and configure local backend with SQLite',
                  'Verify GitHub permissions and branch protection rules',
                  'Confirm campus SSO staging authentication domain',
                ].map((item, idx) => (
                  <label key={idx} className="flex items-center gap-2 text-xs text-slate-700 cursor-pointer">
                    <input type="checkbox" className="rounded border-slate-300 text-navy focus:ring-navy" />
                    <span>{item}</span>
                  </label>
                ))}
              </div>
            </div>

            <div className="space-y-2 pt-2 border-t border-slate-100">
              <h4 className="text-xs font-bold text-navy uppercase tracking-wider">Days 3 - 5: Architecture Shadowing & Releases</h4>
              <div className="space-y-1.5 pl-2">
                {[
                  'Run end-to-end integration test on local Docker compose',
                  'Meet with Mr. Kapoor regarding hostel network port forwarding',
                  'Review unowned PR #9 (Notification service queue) and assign successor',
                ].map((item, idx) => (
                  <label key={idx} className="flex items-center gap-2 text-xs text-slate-700 cursor-pointer">
                    <input type="checkbox" className="rounded border-slate-300 text-navy focus:ring-navy" />
                    <span>{item}</span>
                  </label>
                ))}
              </div>
            </div>
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
            {sections.unresolved?.claims.map((claim) => (
              <div key={claim.id} className="p-3 bg-white rounded-lg border border-amber-200 shadow-xs flex justify-between items-start gap-3">
                <div>
                  <p className="text-xs font-semibold text-slate-900">{claim.text}</p>
                  <span className="text-[11px] text-slate-500 font-mono mt-0.5 block">
                    Subject: {claim.subject_key}
                  </span>
                </div>
                <StatusBadge status={claim.status} isLeaverAttested={claim.created_by === 'leaver'} size="sm" />
              </div>
            ))}
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
