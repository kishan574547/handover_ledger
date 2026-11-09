import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  FileText,
  Edit2,
  Check,
  X,
  AlertTriangle,
  HelpCircle,
  MessageSquare,
  ShieldAlert,
  Layers,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  Send,
  ExternalLink,
} from 'lucide-react';
import { api } from '../../api/client';
import { ClaimItem, ClaimDetail } from '../../types';
import { useRole } from '../../context/RoleContext';
import { useToast } from '../../context/ToastContext';
import { Drawer } from '../common/Drawer';
import { Button } from '../common/Button';
import { StatusBadge, ClearanceBadge, ClaimTypeBadge } from '../common/Badge';

interface EvidenceDrawerProps {
  claimId: string | null;
  onClose: () => void;
  onAskLeaver?: (claimText: string, claimId: string) => void;
}

export const EvidenceDrawer: React.FC<EvidenceDrawerProps> = ({ claimId, onClose, onAskLeaver }) => {
  const { canLead, role } = useRole();
  const { success, error } = useToast();
  const queryClient = useQueryClient();

  const [isEditing, setIsEditing] = useState(false);
  const [editText, setEditText] = useState('');
  const [showSurrounding, setShowSurrounding] = useState<Record<string, boolean>>({});
  const [newComment, setNewComment] = useState('');
  const [customResolution, setCustomResolution] = useState('');
  const [showCustomInput, setShowCustomInput] = useState(false);

  // Fetch full claim detail
  const { data: claim, isLoading } = useQuery<ClaimDetail>({
    queryKey: ['claim-detail', claimId],
    queryFn: () => api.getClaimDetail(claimId!),
    enabled: !!claimId,
  });

  // Update claim mutation
  const updateClaimMutation = useMutation({
    mutationFn: (data: { text?: string; review_state?: string; note?: string }) =>
      api.updateClaim(claimId!, data),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ['claims'] });
      queryClient.invalidateQueries({ queryKey: ['claim-detail', claimId] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      setIsEditing(false);
      success('Claim Updated', `Claim marked as ${updated.review_state}.`);
    },
    onError: (err: any) => error('Update Failed', err.message),
  });

  // Resolve conflict mutation
  const resolveConflictMutation = useMutation({
    mutationFn: (data: { choice: string; text?: string }) =>
      api.resolveConflict(claimId!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['claims'] });
      queryClient.invalidateQueries({ queryKey: ['claim-detail', claimId] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      success('Conflict Resolved', 'Authoritative record updated and resolution note logged.');
    },
    onError: (err: any) => error('Resolution Failed', err.message),
  });

  // Add comment mutation
  const addCommentMutation = useMutation({
    mutationFn: (text: string) => api.addClaimComment(claimId!, text),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['claim-detail', claimId] });
      setNewComment('');
      success('Comment Posted', 'Comment added to claim audit record.');
    },
    onError: (err: any) => error('Comment Failed', err.message),
  });

  if (!claimId) return null;

  const toggleSurrounding = (id: string) => {
    setShowSurrounding((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const handleStartEdit = () => {
    if (claim) {
      setEditText(claim.text);
      setIsEditing(true);
    }
  };

  const handleSaveEdit = () => {
    if (!editText.trim()) return;
    updateClaimMutation.mutate({ text: editText.trim() });
  };

  return (
    <Drawer
      isOpen={!!claimId}
      onClose={onClose}
      title="Evidence & Verification Details"
      subtitle={claim ? `Claim ID: ${claim.id.slice(0, 8)} • Subject: ${claim.subject_key}` : 'Loading...'}
      footer={
        canLead && claim ? (
          <div className="w-full flex items-center justify-between">
            <span className="text-xs text-slate-500">
              Review State: <strong>{claim.review_state.toUpperCase()}</strong>
            </span>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => updateClaimMutation.mutate({ review_state: 'rejected' })}
                disabled={claim.review_state === 'rejected'}
              >
                Reject Claim
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={() => updateClaimMutation.mutate({ review_state: 'approved' })}
                disabled={claim.review_state === 'approved'}
              >
                Approve Claim
              </Button>
            </div>
          </div>
        ) : null
      }
    >
      {isLoading || !claim ? (
        <div className="space-y-4 animate-pulse">
          <div className="h-20 bg-slate-100 rounded-lg" />
          <div className="h-40 bg-slate-100 rounded-lg" />
        </div>
      ) : (
        <div className="space-y-6 text-sm">
          {/* Claim Text Card with Edit */}
          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <ClaimTypeBadge type={claim.type} size="sm" />
                <ClearanceBadge clearance={claim.clearance} size="sm" />
              </div>
              {canLead && !isEditing && (
                <Button variant="ghost" size="sm" onClick={handleStartEdit} leftIcon={<Edit2 className="w-3.5 h-3.5" />}>
                  Edit text
                </Button>
              )}
            </div>

            {isEditing ? (
              <div className="space-y-2 mt-2">
                <textarea
                  value={editText}
                  onChange={(e) => setEditText(e.target.value)}
                  className="w-full text-sm p-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-navy focus:outline-none"
                  rows={3}
                />
                <div className="flex justify-end gap-2">
                  <Button variant="outline" size="sm" onClick={() => setIsEditing(false)}>
                    Cancel
                  </Button>
                  <Button variant="primary" size="sm" onClick={handleSaveEdit} isLoading={updateClaimMutation.isPending}>
                    Save Changes
                  </Button>
                </div>
              </div>
            ) : (
              <p className="text-slate-900 font-medium text-base leading-snug">{claim.text}</p>
            )}

            {claim.owner_name && (
              <div className="mt-3 pt-2 border-t border-slate-200/60 flex items-center gap-2 text-xs text-slate-600">
                <span className="font-medium text-slate-500">Attributed Owner:</span>
                <span className="font-semibold text-slate-800">{claim.owner_name}</span>
                {claim.event_date && (
                  <>
                    <span>•</span>
                    <span>{claim.event_date}</span>
                  </>
                )}
              </div>
            )}
          </div>

          {/* Status & Why This Status */}
          <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Audit Status</span>
              <StatusBadge status={claim.status} isLeaverAttested={claim.created_by === 'leaver'} />
            </div>
            <div className="text-xs text-slate-600 bg-slate-50 p-2.5 rounded-lg border border-slate-100">
              <strong className="text-slate-800">Why this status: </strong>
              {claim.status === 'verified' &&
                'Dual-check passed: Exact quote verified inside source text with rapidfuzz fuzzy-match >= 90% and confirmed by independent verification.'}
              {claim.status === 'inferred' &&
                (claim.created_by === 'leaver'
                  ? 'Attested by the departing team member during exit interview. Not independently verified against code repository.'
                  : 'Passage exists but provides partial or contextual support rather than absolute verbatim proof.')}
              {claim.status === 'conflicting' &&
                'Contradicts another recorded project source for this subject. Requires lead review to determine the authoritative truth.'}
              {claim.status === 'missing' &&
                'An essential rationale, owner, dependency, or status update was missing from documented records.'}
            </div>
          </div>

          {/* Conflict Resolution Side-by-Side (if conflicting) */}
          {claim.status === 'conflicting' && claim.conflict_link && (
            <div className="p-4 bg-rose-50/60 rounded-xl border border-rose-200 space-y-3">
              <div className="flex items-center gap-2 text-rose-800 font-semibold text-xs">
                <AlertTriangle className="w-4 h-4 text-rose-600" />
                <span>Conflicting Claim Discrepancy</span>
              </div>
              <div className="grid grid-cols-1 gap-2 text-xs">
                <div className="p-2.5 bg-white rounded-lg border border-rose-200">
                  <span className="font-semibold text-slate-700">Claim A (Current):</span>
                  <p className="mt-1 text-slate-900">{claim.text}</p>
                </div>
                {claim.conflicting_claim && (
                  <div className="p-2.5 bg-white rounded-lg border border-rose-200">
                    <span className="font-semibold text-slate-700">Claim B (Alternative):</span>
                    <p className="mt-1 text-slate-900">{claim.conflicting_claim.text}</p>
                  </div>
                )}
              </div>

              {canLead && (
                <div className="pt-2 border-t border-rose-200/80 space-y-2">
                  <span className="text-[11px] font-semibold text-slate-700">Lead Resolution Action:</span>
                  <div className="grid grid-cols-2 gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => resolveConflictMutation.mutate({ choice: 'keep_a' })}
                      isLoading={resolveConflictMutation.isPending}
                    >
                      Keep Current (A)
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => resolveConflictMutation.mutate({ choice: 'keep_b' })}
                      isLoading={resolveConflictMutation.isPending}
                    >
                      Keep Alternative (B)
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => resolveConflictMutation.mutate({ choice: 'keep_both' })}
                      isLoading={resolveConflictMutation.isPending}
                    >
                      Keep Both Unresolved
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setShowCustomInput(!showCustomInput)}
                    >
                      Custom Resolution...
                    </Button>
                  </div>
                  {showCustomInput && (
                    <div className="mt-2 space-y-2">
                      <textarea
                        value={customResolution}
                        onChange={(e) => setCustomResolution(e.target.value)}
                        placeholder="Type authoritative reconciled text..."
                        className="w-full text-xs p-2 border border-slate-300 rounded-lg"
                        rows={2}
                      />
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={() =>
                          resolveConflictMutation.mutate({
                            choice: 'custom',
                            text: customResolution,
                          })
                        }
                      >
                        Submit Reconciled Claim
                      </Button>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Missing Gap Box (if missing) */}
          {claim.status === 'missing' && (
            <div className="p-4 bg-slate-100 rounded-xl border border-slate-300 space-y-2">
              <div className="flex items-center gap-2 text-slate-800 font-semibold text-xs">
                <HelpCircle className="w-4 h-4 text-slate-600" />
                <span>Information Gap Identified</span>
              </div>
              <p className="text-xs text-slate-600">
                This item represents missing project knowledge identified during automatic extraction.
              </p>
              {onAskLeaver && (
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => onAskLeaver(claim.text, claim.id)}
                  leftIcon={<HelpCircle className="w-3.5 h-3.5" />}
                >
                  Ask the Leaver in Interview
                </Button>
              )}
            </div>
          )}

          {/* Evidence Blocks */}
          <div className="space-y-3">
            <h4 className="text-xs font-semibold text-slate-700 uppercase tracking-wider flex items-center justify-between">
              <span>Evidentiary Passages ({claim.evidence.length})</span>
            </h4>

            {claim.evidence.length === 0 ? (
              <p className="text-xs text-slate-400 italic">No direct source passages attached.</p>
            ) : (
              claim.evidence.map((ev, idx) => (
                <div key={idx} className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm space-y-3">
                  <div className="flex items-start justify-between text-xs">
                    <div>
                      <span className="font-semibold text-slate-800">{ev.source_name || 'Project Source'}</span>
                      <p className="text-[11px] text-slate-500 font-mono mt-0.5">{ev.location_label || 'Location unrecorded'}</p>
                    </div>
                    <div className="text-right">
                      <span className="inline-block px-2 py-0.5 rounded bg-slate-100 text-[11px] font-mono text-slate-700">
                        Match: {Math.round(ev.match_score)}%
                      </span>
                    </div>
                  </div>

                  {/* Monospace Quote Box */}
                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 font-mono text-xs text-slate-800 leading-relaxed overflow-x-auto">
                    <span className="bg-amber-100/90 text-amber-950 px-1 py-0.5 rounded font-semibold">
                      &quot;{ev.quote}&quot;
                    </span>
                  </div>

                  {/* Verifier Result Panel */}
                  <div className="text-xs bg-slate-50 p-2.5 rounded-lg border border-slate-200/80 flex items-start gap-2 text-slate-700">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <div className="font-medium text-slate-800">
                        Passage Found: {ev.match_score >= 90 ? 'Yes (>= 90%)' : 'No (< 90%)'} • Support: {ev.support.toUpperCase()}
                      </div>
                      <p className="text-[11px] text-slate-500 mt-0.5">{ev.reason || 'Verification logic applied.'}</p>
                    </div>
                  </div>

                  {/* Surrounding Context Toggle */}
                  {ev.surrounding_text && (
                    <div className="pt-1">
                      <button
                        onClick={() => toggleSurrounding(ev.id)}
                        className="text-xs text-navy hover:text-navy-hover font-medium flex items-center gap-1"
                      >
                        {showSurrounding[ev.id] ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                        <span>{showSurrounding[ev.id] ? 'Hide surrounding text' : 'Show surrounding text'}</span>
                      </button>
                      {showSurrounding[ev.id] && (
                        <div className="mt-2 p-3 bg-slate-900 text-slate-200 text-xs font-mono rounded-lg max-h-40 overflow-y-auto whitespace-pre-wrap">
                          {ev.surrounding_text}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>

          {/* Comments and Audit Notes */}
          <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm space-y-3">
            <h4 className="text-xs font-semibold text-slate-700 uppercase tracking-wider flex items-center gap-2">
              <MessageSquare className="w-3.5 h-3.5 text-slate-500" />
              <span>Review Comments ({claim.comments.length})</span>
            </h4>

            {claim.comments.length > 0 && (
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {claim.comments.map((cm) => (
                  <div key={cm.id} className="p-2.5 bg-slate-50 rounded-lg text-xs space-y-1">
                    <div className="flex justify-between items-center text-[11px] text-slate-500">
                      <strong className="text-slate-800 capitalize">{cm.role}</strong>
                      <span>{new Date(cm.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    </div>
                    <p className="text-slate-700">{cm.text}</p>
                  </div>
                ))}
              </div>
            )}

            <div className="flex items-center gap-2 pt-2 border-t border-slate-100">
              <input
                type="text"
                placeholder="Add audit note or comment..."
                value={newComment}
                onChange={(e) => setNewComment(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && newComment.trim() && addCommentMutation.mutate(newComment.trim())}
                className="flex-1 text-xs px-3 py-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-navy focus:outline-none"
              />
              <Button
                variant="secondary"
                size="sm"
                disabled={!newComment.trim()}
                onClick={() => addCommentMutation.mutate(newComment.trim())}
              >
                <Send className="w-3.5 h-3.5" />
              </Button>
            </div>
          </div>
        </div>
      )}
    </Drawer>
  );
};

