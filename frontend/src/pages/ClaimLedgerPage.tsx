import React, { useState, useMemo } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Search,
  Filter,
  CheckCircle2,
  XCircle,
  FileSpreadsheet,
  AlertTriangle,
  RotateCcw,
  Check,
  X,
  Lock,
} from 'lucide-react';
import { api } from '../api/client';
import { ClaimItem, ClaimType, ClaimStatus, ReviewState } from '../types';
import { useRole } from '../context/RoleContext';
import { useToast } from '../context/ToastContext';
import { Card, CardHeader, CardTitle, CardContent } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Modal } from '../components/common/Modal';
import { ClaimRow } from '../components/ledger/ClaimRow';
import { EvidenceDrawer } from '../components/ledger/EvidenceDrawer';
import { TableRowSkeleton } from '../components/common/Skeleton';

export const ClaimLedgerPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { canLead, role } = useRole();
  const { success, error } = useToast();
  const queryClient = useQueryClient();

  // Filters from URL query params
  const searchQuery = searchParams.get('q') || '';
  const selectedType = searchParams.get('type') || '';
  const selectedStatus = searchParams.get('status') || '';
  const selectedClearance = searchParams.get('clearance') || '';
  const selectedReviewState = searchParams.get('review_state') || '';
  const selectedSort = searchParams.get('sort') || 'event_date_desc';

  // Local state
  const [selectedClaimId, setSelectedClaimId] = useState<string | null>(null);
  const [rejectClaimId, setRejectClaimId] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const [showApproveAllModal, setShowApproveAllModal] = useState(false);

  // Fetch claims with database query layer clearance enforcement
  const { data: claims, isLoading } = useQuery<ClaimItem[]>({
    queryKey: ['claims', selectedType, selectedStatus, selectedClearance, selectedReviewState, searchQuery, selectedSort],
    queryFn: () =>
      api.getClaims({
        type: selectedType,
        status: selectedStatus,
        clearance: selectedClearance ? Number(selectedClearance) : undefined,
        review_state: selectedReviewState,
        q: searchQuery,
        sort: selectedSort,
        include_restricted: true,
      }),
  });

  // Count verified pending claims for "Approve all verified" button
  const verifiedPendingCount = useMemo(() => {
    if (!claims) return 0;
    return claims.filter((c) => c.status === 'verified' && c.review_state === 'pending' && !c.is_hidden).length;
  }, [claims]);

  // Mutations
  const updateClaimMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: { review_state?: string; note?: string } }) =>
      api.updateClaim(id, data),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['claims'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      setRejectClaimId(null);
      setRejectReason('');
      success('Claim Updated', `Review state updated to ${res.review_state}.`);
    },
    onError: (err: any) => error('Update Failed', err.message),
  });

  const approveAllMutation = useMutation({
    mutationFn: api.approveAllVerified,
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['claims'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      setShowApproveAllModal(false);
      success('Batch Approval Complete', `Approved ${res.approved_count} verified claims.`);
    },
    onError: (err: any) => error('Approval Failed', err.message),
  });

  const handleFilterChange = (key: string, value: string) => {
    const nextParams = new URLSearchParams(searchParams);
    if (value) {
      nextParams.set(key, value);
    } else {
      nextParams.delete(key);
    }
    setSearchParams(nextParams);
  };

  const handleClearFilters = () => {
    setSearchParams(new URLSearchParams());
  };

  // Chips data
  const claimTypes: { id: ClaimType; label: string }[] = [
    { id: 'decision', label: 'Decision' },
    { id: 'open_work', label: 'Open Work' },
    { id: 'owner', label: 'Owner' },
    { id: 'risk', label: 'Risk' },
    { id: 'dependency', label: 'Dependency' },
    { id: 'contact', label: 'Contact' },
    { id: 'recurring_problem', label: 'Recurring Problem' },
    { id: 'next_action', label: 'Next Action' },
    { id: 'change', label: 'Change' },
  ];

  const statuses: { id: ClaimStatus; label: string }[] = [
    { id: 'verified', label: 'Verified' },
    { id: 'inferred', label: 'Inferred' },
    { id: 'conflicting', label: 'Conflicting' },
    { id: 'missing', label: 'Missing' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Claim Ledger</h2>
          <p className="text-sm text-slate-500 mt-1">
            Complete atomic ledger of verified, inferred, conflicting, and missing project assertions.
          </p>
        </div>

        {canLead && (
          <div className="flex items-center gap-2">
            <Button
              variant="primary"
              size="sm"
              onClick={() => setShowApproveAllModal(true)}
              disabled={verifiedPendingCount === 0}
              leftIcon={<CheckCircle2 className="w-4 h-4" />}
            >
              Approve All Verified ({verifiedPendingCount})
            </Button>
          </div>
        )}
      </div>

      {/* Filter Bar Card */}
      <Card className="p-4 space-y-3 bg-white">
        {/* Top search & selectors row */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Search box */}
          <div className="relative flex-1 min-w-[240px]">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search claims, owners, subjects..."
              value={searchQuery}
              onChange={(e) => handleFilterChange('q', e.target.value)}
              className="w-full text-xs pl-9 pr-3 py-2 border border-slate-300 rounded-lg focus:ring-1 focus:ring-navy focus:outline-none"
            />
          </div>

          {/* Clearance Select */}
          <select
            value={selectedClearance}
            onChange={(e) => handleFilterChange('clearance', e.target.value)}
            className="text-xs py-2 px-3 border border-slate-300 rounded-lg bg-white text-slate-700"
          >
            <option value="">All Clearances</option>
            <option value="1">Level 1: General</option>
            <option value="2">Level 2: Technical</option>
            <option value="3">Level 3: Confidential</option>
          </select>

          {/* Review State Select */}
          <select
            value={selectedReviewState}
            onChange={(e) => handleFilterChange('review_state', e.target.value)}
            className="text-xs py-2 px-3 border border-slate-300 rounded-lg bg-white text-slate-700"
          >
            <option value="">All Review States</option>
            <option value="pending">Pending Review</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
          </select>

          {/* Sort Select */}
          <select
            value={selectedSort}
            onChange={(e) => handleFilterChange('sort', e.target.value)}
            className="text-xs py-2 px-3 border border-slate-300 rounded-lg bg-white text-slate-700 font-mono"
          >
            <option value="event_date_desc">Sort: Newest Date</option>
            <option value="event_date_asc">Sort: Oldest Date</option>
            <option value="clearance_desc">Sort: Highest Clearance</option>
            <option value="status">Sort: By Status</option>
          </select>

          {/* Clear Filters Button */}
          {(searchQuery || selectedType || selectedStatus || selectedClearance || selectedReviewState) && (
            <Button variant="ghost" size="sm" onClick={handleClearFilters} leftIcon={<RotateCcw className="w-3.5 h-3.5" />}>
              Clear filters
            </Button>
          )}
        </div>

        {/* Type & Status Filter Chips */}
        <div className="pt-2 border-t border-slate-100 flex flex-wrap items-center gap-2">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mr-1">Status:</span>
          {statuses.map((st) => {
            const isActive = selectedStatus === st.id;
            return (
              <button
                key={st.id}
                onClick={() => handleFilterChange('status', isActive ? '' : st.id)}
                className={`text-xs px-2.5 py-1 rounded-full border transition-all ${
                  isActive
                    ? 'bg-navy text-white border-navy font-semibold'
                    : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
                }`}
              >
                {st.label}
              </button>
            );
          })}

          <div className="h-4 w-px bg-slate-200 mx-2" />

          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mr-1">Type:</span>
          <div className="flex flex-wrap items-center gap-1.5">
            {claimTypes.map((ct) => {
              const isActive = selectedType === ct.id;
              return (
                <button
                  key={ct.id}
                  onClick={() => handleFilterChange('type', isActive ? '' : ct.id)}
                  className={`text-xs px-2.5 py-1 rounded-lg border transition-all ${
                    isActive
                      ? 'bg-navy text-white border-navy font-semibold'
                      : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
                  }`}
                >
                  {ct.label}
                </button>
              );
            })}
          </div>
        </div>
      </Card>

      {/* Claims Table */}
      <Card>
        <CardContent className="p-0 overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50/80 border-b border-slate-200 text-[11px] font-semibold text-slate-600 uppercase tracking-wider">
                <th className="py-3 px-4">Type</th>
                <th className="py-3 px-4">Claim Statement</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Clearance</th>
                <th className="py-3 px-4">Owner</th>
                <th className="py-3 px-4">Evidence</th>
                <th className="py-3 px-4">Review State</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                Array.from({ length: 6 }).map((_, i) => <TableRowSkeleton key={i} cols={8} />)
              ) : !claims || claims.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    <FileSpreadsheet className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    <p className="text-sm font-medium text-slate-600">No claims match the selected filters.</p>
                    <p className="text-xs text-slate-400 mt-1">Try clearing or adjusting search and filters.</p>
                  </td>
                </tr>
              ) : (
                claims.map((claim) => (
                  <ClaimRow
                    key={claim.id}
                    claim={claim}
                    onViewEvidence={(id) => setSelectedClaimId(id)}
                    onApprove={(id) => updateClaimMutation.mutate({ id, data: { review_state: 'approved' } })}
                    onReject={(id) => setRejectClaimId(id)}
                  />
                ))
              )}
            </tbody>
          </table>
        </CardContent>
      </Card>

      {/* Reject Reason Modal */}
      <Modal
        isOpen={!!rejectClaimId}
        onClose={() => {
          setRejectClaimId(null);
          setRejectReason('');
        }}
        title="Reject Claim from Handover"
        description="Provide an audit note explaining why this claim was rejected or contradicted."
        footer={
          <>
            <Button variant="outline" size="sm" onClick={() => setRejectClaimId(null)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              size="sm"
              isLoading={updateClaimMutation.isPending}
              onClick={() => {
                if (rejectClaimId) {
                  updateClaimMutation.mutate({
                    id: rejectClaimId,
                    data: { review_state: 'rejected', note: rejectReason || 'Rejected by Project Lead' },
                  });
                }
              }}
            >
              Confirm Rejection
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <label className="text-xs font-semibold text-slate-700 block">Rejection Reason / Note</label>
          <textarea
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
            placeholder="e.g. Obsolete config, superseded by subsequent sprint meeting..."
            className="w-full text-xs p-3 border border-slate-300 rounded-lg focus:ring-1 focus:ring-rose-500 focus:outline-none"
            rows={3}
          />
        </div>
      </Modal>

      {/* Approve All Verified Modal */}
      <Modal
        isOpen={showApproveAllModal}
        onClose={() => setShowApproveAllModal(false)}
        title="Approve All Verified Claims?"
        description="Batch approval of all claims where quotes were verified with >= 90% match and independent support confirmed."
        footer={
          <>
            <Button variant="outline" size="sm" onClick={() => setShowApproveAllModal(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              isLoading={approveAllMutation.isPending}
              onClick={() => approveAllMutation.mutate()}
            >
              Approve {verifiedPendingCount} Claims
            </Button>
          </>
        }
      >
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-900 flex items-start gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
          <p>
            This action will mark all <strong>{verifiedPendingCount} pending verified claims</strong> as approved.
            Inferred, conflicting, and missing claims will remain pending lead review.
          </p>
        </div>
      </Modal>

      {/* Evidence Drawer */}
      <EvidenceDrawer
        claimId={selectedClaimId}
        onClose={() => setSelectedClaimId(null)}
        onAskLeaver={() => {
          setSelectedClaimId(null);
          navigate('/interview');
        }}
      />
    </div>
  );
};
