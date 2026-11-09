import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  CheckSquare,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  GitCompare,
  ArrowRight,
  ShieldCheck,
  Send,
  Save,
  RotateCcw,
  Clock,
  Sparkles,
} from 'lucide-react';
import { api } from '../api/client';
import { ReviewSummary, HandoverVersionItem } from '../types';
import { useRole } from '../context/RoleContext';
import { useToast } from '../context/ToastContext';
import { Card, CardHeader, CardTitle, CardContent } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Modal } from '../components/common/Modal';

export const ReviewApprovePage: React.FC = () => {
  const navigate = useNavigate();
  const { canLead, role } = useRole();
  const { success, error, warning } = useToast();
  const queryClient = useQueryClient();

  // Modals state
  const [showDraftModal, setShowDraftModal] = useState(false);
  const [draftNote, setDraftNote] = useState('');

  const [showSendBackModal, setShowSendBackModal] = useState(false);
  const [sendBackNote, setSendBackNote] = useState('');

  const [showApproveModal, setShowApproveModal] = useState(false);
  const [approveNote, setApproveNote] = useState('');
  const [acceptOpenItems, setAcceptOpenItems] = useState(false);

  // Compare diff modal
  const [showDiffModal, setShowDiffModal] = useState(false);
  const [diffVerA, setDiffVerA] = useState<number>(1);
  const [diffVerB, setDiffVerB] = useState<number>(2);
  const [diffData, setDiffData] = useState<any>(null);
  const [isDiffLoading, setIsDiffLoading] = useState(false);

  // Fetch summary checklist
  const { data: summary, isLoading } = useQuery<ReviewSummary>({
    queryKey: ['review-summary'],
    queryFn: api.getReviewSummary,
  });

  // Fetch versions
  const { data: versions } = useQuery<HandoverVersionItem[]>({
    queryKey: ['handover-versions'],
    queryFn: api.getVersions,
  });

  // Mutations
  const createVersionMutation = useMutation({
    mutationFn: (note?: string) => api.createVersion(note),
    onSuccess: (ver) => {
      queryClient.invalidateQueries({ queryKey: ['handover-versions'] });
      queryClient.invalidateQueries({ queryKey: ['review-summary'] });
      setShowDraftModal(false);
      setDraftNote('');
      success('Version Saved', `Saved draft handover Version #${ver.number}.`);
    },
    onError: (err: any) => error('Version Failed', err.message),
  });

  const sendBackMutation = useMutation({
    mutationFn: (note: string) => api.sendBackHandover(note),
    onSuccess: () => {
      queryClient.invalidateQueries();
      setShowSendBackModal(false);
      setSendBackNote('');
      warning('Handover Sent Back', 'Status updated to "sent_back" for further revisions.');
    },
    onError: (err: any) => error('Send Back Failed', err.message),
  });

  const approveHandoverMutation = useMutation({
    mutationFn: (data: { note?: string; accept_open_items: boolean }) =>
      api.approveHandover(data.note, data.accept_open_items),
    onSuccess: () => {
      queryClient.invalidateQueries();
      setShowApproveModal(false);
      success('Handover Released', 'Handover has been approved and released to incoming roles.');
    },
    onError: (err: any) => error('Approval Failed', err.message),
  });

  const handleOpenDiff = async (vA: number, vB: number) => {
    setIsDiffLoading(true);
    setShowDiffModal(true);
    setDiffVerA(vA);
    setDiffVerB(vB);
    try {
      const diff = await api.compareVersions(vA, vB);
      setDiffData(diff);
    } catch (err: any) {
      error('Diff Error', err.message);
    } finally {
      setIsDiffLoading(false);
    }
  };

  if (!canLead) {
    return (
      <Card className="p-12 text-center text-slate-500">
        <AlertTriangle className="w-8 h-8 text-amber-500 mx-auto mb-2" />
        <h3 className="text-base font-semibold text-slate-900">Restricted to Project Lead</h3>
        <p className="text-xs text-slate-500 mt-1">
          Only the Project Lead (Priya Nair) has administrative permission to review checklists, save versions, and release the handover.
        </p>
      </Card>
    );
  }

  const isApproved = summary?.handover_status === 'approved';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Review & Handover Approval</h2>
          <p className="text-sm text-slate-500 mt-1">
            Audit readiness checklist, manage release versions, and approve the authoritative handover for incoming members.
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowDraftModal(true)}
            leftIcon={<Save className="w-4 h-4" />}
          >
            Save Draft Version
          </Button>

          <Button
            variant="secondary"
            size="sm"
            onClick={() => setShowSendBackModal(true)}
            leftIcon={<RotateCcw className="w-4 h-4 text-rose-600" />}
          >
            Send Back for Changes
          </Button>

          <Button
            variant="accent"
            size="sm"
            onClick={() => setShowApproveModal(true)}
            disabled={isApproved}
            leftIcon={<ShieldCheck className="w-4 h-4" />}
          >
            {isApproved ? 'Handover Released' : 'Approve & Release Handover'}
          </Button>
        </div>
      </div>

      {/* Green Approved Success Banner (if approved) */}
      {isApproved && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-card flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="w-6 h-6 text-emerald-600 flex-shrink-0" />
            <div>
              <h4 className="text-sm font-semibold text-emerald-950">Handover Approved and Released</h4>
              <p className="text-xs text-emerald-800 mt-0.5">
                The handover is now officially released. Incoming developers and coordinators can view sections within their clearance.
              </p>
            </div>
          </div>
          <Button variant="primary" size="sm" onClick={() => navigate('/handover')} rightIcon={<ArrowRight className="w-4 h-4" />}>
            View Handover
          </Button>
        </div>
      )}

      {/* Readiness Checklist Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold text-slate-900">
            Handover Release Readiness Checklist
          </CardTitle>
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-500 uppercase">Readiness Score:</span>
            <span className="text-sm font-bold text-navy bg-navy/10 px-2 py-0.5 rounded">
              {summary?.readiness_percent || 0}%
            </span>
          </div>
        </CardHeader>
        <CardContent className="divide-y divide-slate-100 p-0">
          {summary?.checklist.map((item) => (
            <div key={item.id} className="p-4 flex items-center justify-between hover:bg-slate-50 transition-colors">
              <div className="flex items-start gap-3">
                <div className="mt-0.5 flex-shrink-0">
                  {item.passed ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                  ) : (
                    <AlertTriangle className="w-5 h-5 text-amber-500" />
                  )}
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-slate-900">{item.title}</h4>
                  <p className="text-xs text-slate-500 mt-0.5">{item.message}</p>
                </div>
              </div>

              {!item.passed && (
                <Button variant="ghost" size="sm" onClick={() => navigate(item.fix_link)} rightIcon={<ArrowRight className="w-3.5 h-3.5" />}>
                  Fix this
                </Button>
              )}
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Version History Table with Compare */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold text-slate-900">
            Handover Version Snapshots ({versions?.length || 0})
          </CardTitle>
          <span className="text-xs text-slate-500">
            Immutable snapshots of claims and verified records across review stages.
          </span>
        </CardHeader>
        <CardContent className="p-0 overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 text-[11px] font-semibold text-slate-600 uppercase tracking-wider border-b border-slate-200">
                <th className="py-3 px-5">Version #</th>
                <th className="py-3 px-4">Created Time</th>
                <th className="py-3 px-4">Audit Note</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-sm">
              {!versions || versions.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-slate-400 text-xs">
                    No version snapshots saved yet. Click &quot;Save Draft Version&quot; to freeze a snapshot.
                  </td>
                </tr>
              ) : (
                versions.map((ver, idx) => (
                  <tr key={ver.id} className="hover:bg-slate-50">
                    <td className="py-3 px-5 font-mono font-bold text-navy">
                      v{ver.number}.0
                    </td>
                    <td className="py-3 px-4 text-xs text-slate-600">
                      {new Date(ver.created_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}
                    </td>
                    <td className="py-3 px-4 text-xs text-slate-800">
                      {ver.note || 'No note recorded'}
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-[11px] font-semibold uppercase ${
                          ver.status === 'approved'
                            ? 'bg-emerald-100 text-emerald-800'
                            : ver.status === 'sent_back'
                            ? 'bg-rose-100 text-rose-800'
                            : 'bg-slate-100 text-slate-700'
                        }`}
                      >
                        {ver.status}
                      </span>
                    </td>
                    <td className="py-3 px-5 text-right">
                      {versions.length > 1 && idx < versions.length - 1 && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleOpenDiff(versions[idx + 1].number, ver.number)}
                          leftIcon={<GitCompare className="w-3.5 h-3.5" />}
                        >
                          Compare with v{versions[idx + 1].number}
                        </Button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </CardContent>
      </Card>

      {/* Save Draft Version Modal */}
      <Modal
        isOpen={showDraftModal}
        onClose={() => setShowDraftModal(false)}
        title="Save Draft Version Snapshot"
        description="Creates an immutable snapshot of all claims and review states at this moment."
        footer={
          <>
            <Button variant="outline" size="sm" onClick={() => setShowDraftModal(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              isLoading={createVersionMutation.isPending}
              onClick={() => createVersionMutation.mutate(draftNote.trim() || undefined)}
            >
              Save Snapshot
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <label className="text-xs font-semibold text-slate-700 block">Version Note</label>
          <input
            type="text"
            placeholder="e.g. Pre-handover sprint review; resolved API timeout conflict"
            value={draftNote}
            onChange={(e) => setDraftNote(e.target.value)}
            className="w-full text-xs p-3 border border-slate-300 rounded-lg focus:ring-1 focus:ring-navy focus:outline-none"
          />
        </div>
      </Modal>

      {/* Send Back Modal */}
      <Modal
        isOpen={showSendBackModal}
        onClose={() => setShowSendBackModal(false)}
        title="Send Back Handover for Revisions"
        description="Notify departing team member that additional gaps or clarifications are required."
        footer={
          <>
            <Button variant="outline" size="sm" onClick={() => setShowSendBackModal(false)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              size="sm"
              disabled={!sendBackNote.trim()}
              isLoading={sendBackMutation.isPending}
              onClick={() => sendBackMutation.mutate(sendBackNote.trim())}
            >
              Send Back
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <label className="text-xs font-semibold text-slate-700 block">Required Changes Note (Mandatory)</label>
          <textarea
            rows={3}
            placeholder="Specify what missing knowledge or unanswered questions need attention..."
            value={sendBackNote}
            onChange={(e) => setSendBackNote(e.target.value)}
            className="w-full text-xs p-3 border border-slate-300 rounded-lg focus:ring-1 focus:ring-rose-500 focus:outline-none"
          />
        </div>
      </Modal>

      {/* Approve and Release Modal */}
      <Modal
        isOpen={showApproveModal}
        onClose={() => setShowApproveModal(false)}
        title="Approve and Release Handover?"
        description="Release the authoritative project handover to successors."
        footer={
          <>
            <Button variant="outline" size="sm" onClick={() => setShowApproveModal(false)}>
              Cancel
            </Button>
            <Button
              variant="accent"
              size="sm"
              isLoading={approveHandoverMutation.isPending}
              onClick={() =>
                approveHandoverMutation.mutate({
                  note: approveNote.trim() || undefined,
                  accept_open_items: acceptOpenItems,
                })
              }
            >
              Confirm Release
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-900 space-y-1">
            <strong>Release Summary:</strong>
            <p>
              • {summary?.metrics.approved_claims || 0} claims approved
              <br />
              • {summary?.metrics.unresolved_conflicts || 0} conflicts remaining
              <br />• {summary?.metrics.confidential_claims || 0} confidential items isolated from lower roles
            </p>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-700 block mb-1">Release Note (Optional)</label>
            <input
              type="text"
              placeholder="e.g. Formal sign-off by Club President for graduation handover"
              value={approveNote}
              onChange={(e) => setApproveNote(e.target.value)}
              className="w-full text-xs p-3 border border-slate-300 rounded-lg focus:ring-1 focus:ring-navy focus:outline-none"
            />
          </div>

          <label className="flex items-start gap-2 cursor-pointer pt-2">
            <input
              type="checkbox"
              checked={acceptOpenItems}
              onChange={(e) => setAcceptOpenItems(e.target.checked)}
              className="mt-0.5 rounded border-slate-300 text-navy focus:ring-navy"
            />
            <span className="text-xs text-slate-700">
              I accept the remaining open and missing items; they will be explicitly displayed in the &quot;Unresolved and Uncertain&quot; section for the incoming developers.
            </span>
          </label>
        </div>
      </Modal>

      {/* Version Diff Modal */}
      <Modal
        isOpen={showDiffModal}
        onClose={() => setShowDiffModal(false)}
        title={`Comparing Version ${diffVerA} vs Version ${diffVerB}`}
        description="Audit differences between frozen handover snapshots."
        maxWidth="xl"
      >
        {isDiffLoading ? (
          <div className="py-8 text-center text-slate-400">Loading version diff...</div>
        ) : !diffData ? (
          <div className="py-4 text-center text-slate-500 text-xs">No differences recorded.</div>
        ) : (
          <div className="space-y-4 text-xs">
            <div>
              <h4 className="font-semibold text-emerald-700 mb-1">Added Claims ({diffData.added_claims.length}):</h4>
              {diffData.added_claims.length === 0 ? (
                <p className="text-slate-400 italic">None</p>
              ) : (
                diffData.added_claims.map((c: any) => (
                  <div key={c.id} className="p-2 bg-emerald-50 text-emerald-900 rounded mb-1 border border-emerald-200">
                    + {c.text}
                  </div>
                ))
              )}
            </div>

            <div>
              <h4 className="font-semibold text-rose-700 mb-1">Removed Claims ({diffData.removed_claims.length}):</h4>
              {diffData.removed_claims.length === 0 ? (
                <p className="text-slate-400 italic">None</p>
              ) : (
                diffData.removed_claims.map((c: any) => (
                  <div key={c.id} className="p-2 bg-rose-50 text-rose-900 rounded mb-1 border border-rose-200">
                    - {c.text}
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};
