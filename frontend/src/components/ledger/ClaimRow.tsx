import React from 'react';
import {
  Eye,
  Check,
  X,
  Lock,
  MessageSquare,
  User,
} from 'lucide-react';
import { ClaimItem } from '../../types';
import { useRole } from '../../context/RoleContext';
import { StatusBadge, ClearanceBadge, ClaimTypeBadge } from '../common/Badge';

interface ClaimRowProps {
  claim: ClaimItem;
  onViewEvidence: (claimId: string) => void;
  onApprove?: (claimId: string) => void;
  onReject?: (claimId: string) => void;
}

export const ClaimRow: React.FC<ClaimRowProps> = ({
  claim,
  onViewEvidence,
  onApprove,
  onReject,
}) => {
  const { canLead } = useRole();

  if (claim.is_hidden) {
    return (
      <tr className="border-b border-slate-100 bg-slate-50/70 text-slate-400 select-none">
        <td className="py-3 px-4">
          <div className="flex items-center gap-1.5 text-slate-400">
            <Lock className="w-4 h-4 text-slate-400" />
            <span className="text-xs font-medium">Restricted</span>
          </div>
        </td>
        <td className="py-3 px-4 font-mono text-xs text-slate-400 italic">
          [Restricted item hidden for your role: requires Clearance Level 3]
        </td>
        <td className="py-3 px-4">
          <span className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs bg-slate-200 text-slate-500">
            <Lock className="w-3 h-3" />
            <span>Hidden</span>
          </span>
        </td>
        <td className="py-3 px-4">
          <ClearanceBadge clearance={claim.clearance} size="sm" />
        </td>
        <td className="py-3 px-4 text-xs text-slate-400">—</td>
        <td className="py-3 px-4 text-xs text-slate-400">—</td>
        <td className="py-3 px-4 text-xs text-slate-400">—</td>
        <td className="py-3 px-4 text-right">
          <span className="text-xs text-slate-400 italic">Locked</span>
        </td>
      </tr>
    );
  }

  return (
    <tr className="border-b border-slate-100 hover:bg-slate-50/80 transition-colors group">
      {/* Type */}
      <td className="py-3 px-4 whitespace-nowrap">
        <ClaimTypeBadge type={claim.type} size="sm" />
      </td>

      {/* Claim Text */}
      <td className="py-3 px-4 max-w-md">
        <div className="text-sm font-medium text-slate-900 leading-snug line-clamp-2">
          {claim.text}
        </div>
      </td>

      {/* Status */}
      <td className="py-3 px-4 whitespace-nowrap">
        <StatusBadge status={claim.status} isLeaverAttested={claim.created_by === 'leaver'} size="sm" />
      </td>

      {/* Clearance */}
      <td className="py-3 px-4 whitespace-nowrap">
        <ClearanceBadge clearance={claim.clearance} size="sm" />
      </td>

      {/* Owner */}
      <td className="py-3 px-4 whitespace-nowrap text-xs text-slate-700">
        {claim.owner_name ? (
          <span className="inline-flex items-center gap-1 bg-slate-100 px-2 py-0.5 rounded text-slate-700">
            <User className="w-3 h-3 text-slate-400" />
            <span className="truncate max-w-[120px]">{claim.owner_name}</span>
          </span>
        ) : (
          <span className="text-slate-400 italic">—</span>
        )}
      </td>

      {/* Evidence Count */}
      <td className="py-3 px-4 whitespace-nowrap text-xs text-slate-600 font-mono">
        <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700">
          {claim.evidence_count} {claim.evidence_count === 1 ? 'quote' : 'quotes'}
        </span>
      </td>

      {/* Review State */}
      <td className="py-3 px-4 whitespace-nowrap">
        <span
          className={`inline-block px-2 py-0.5 rounded text-xs font-medium uppercase tracking-wider ${
            claim.review_state === 'approved'
              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
              : claim.review_state === 'rejected'
              ? 'bg-rose-50 text-rose-700 border border-rose-200'
              : 'bg-amber-50 text-amber-700 border border-amber-200'
          }`}
        >
          {claim.review_state}
        </span>
      </td>

      {/* Actions */}
      <td className="py-3 px-4 text-right whitespace-nowrap">
        <div className="flex items-center justify-end gap-1.5">
          <button
            onClick={() => onViewEvidence(claim.id)}
            title="View evidence passage & verification breakdown"
            className="p-1.5 rounded-lg text-slate-500 hover:text-navy hover:bg-slate-100 transition-colors focus:ring-2 focus:ring-navy"
          >
            <Eye className="w-4 h-4" />
          </button>

          {canLead && onApprove && (
            <button
              onClick={() => onApprove(claim.id)}
              disabled={claim.review_state === 'approved'}
              title="Approve claim"
              className="p-1.5 rounded-lg text-emerald-600 hover:bg-emerald-50 transition-colors disabled:opacity-40 focus:ring-2 focus:ring-emerald-500"
            >
              <Check className="w-4 h-4" />
            </button>
          )}

          {canLead && onReject && (
            <button
              onClick={() => onReject(claim.id)}
              disabled={claim.review_state === 'rejected'}
              title="Reject claim"
              className="p-1.5 rounded-lg text-rose-600 hover:bg-rose-50 transition-colors disabled:opacity-40 focus:ring-2 focus:ring-rose-500"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </td>
    </tr>
  );
};

