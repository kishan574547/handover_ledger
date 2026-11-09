import React, { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Clock,
  GitBranch,
  Calendar,
  AlertTriangle,
  Eye,
  CheckCircle,
  HelpCircle,
  Sparkles,
} from 'lucide-react';
import { api } from '../api/client';
import { TimelineItem } from '../types';
import { useRole } from '../context/RoleContext';
import { Card, CardHeader, CardTitle, CardContent } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { StatusBadge, ClearanceBadge } from '../components/common/Badge';
import { EvidenceDrawer } from '../components/ledger/EvidenceDrawer';
import { TrustLens, TrustLensMode, filterClaimsByTrustLens } from '../components/common/TrustLens';

export const TimelinePage: React.FC = () => {
  const { roleConfig } = useRole();
  const [filterType, setFilterType] = useState<string>('all'); // all, decision, change, unresolved
  const [trustMode, setTrustMode] = useState<TrustLensMode>('everything');
  const [selectedClaimId, setSelectedClaimId] = useState<string | null>(null);

  const { data: timelineItems, isLoading } = useQuery<TimelineItem[]>({
    queryKey: ['timeline'],
    queryFn: api.getTimeline,
  });

  // Filter items by type and trust lens
  const filteredItems = useMemo(() => {
    if (!timelineItems) return [];
    let items = timelineItems;
    if (filterType === 'unresolved') {
      items = items.filter((i) => i.is_unresolved);
    } else if (filterType !== 'all') {
      items = items.filter((i) => i.type === filterType);
    }
    return filterClaimsByTrustLens(items, trustMode);
  }, [timelineItems, filterType, trustMode]);

  // Group items by Month-Year
  const groupedByMonth = useMemo(() => {
    const groups: Record<string, TimelineItem[]> = {};
    filteredItems.forEach((item) => {
      let monthYear = 'Unrecorded Date';
      if (item.date && item.date.length >= 7) {
        const d = new Date(item.date);
        if (!isNaN(d.getTime())) {
          monthYear = d.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
        } else {
          monthYear = item.date.slice(0, 7);
        }
      }
      if (!groups[monthYear]) {
        groups[monthYear] = [];
      }
      groups[monthYear].push(item);
    });
    return groups;
  }, [filteredItems]);

  return (
    <div className="space-y-6">
      {/* Standard Page Header Pattern */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6">
        <div>
          <h2 className="page-title text-text-main">Project Evolution Timeline</h2>
          <p className="text-sm text-text-muted mt-1">
            Chronological log of architecture decisions, changes, and open milestones ({roleConfig.clearanceLabel}).
          </p>
        </div>

        {/* Filter Chips */}
        <div className="flex flex-wrap items-center gap-1.5 bg-surface p-1 rounded-card border border-border self-start sm:self-auto">
          {[
            { id: 'all', label: 'All Milestones' },
            { id: 'decision', label: 'Decisions' },
            { id: 'change', label: 'Changes' },
            { id: 'unresolved', label: 'Unresolved Only' },
          ].map((chip) => {
            const isActive = filterType === chip.id;
            return (
              <button
                key={chip.id}
                onClick={() => setFilterType(chip.id)}
                className={`px-3 py-1.5 rounded-btn text-xs font-medium transition-all min-h-[32px] ${
                  isActive
                    ? 'bg-navy text-white dark:bg-teal dark:text-white font-semibold shadow-sm'
                    : 'text-text-muted hover:text-text-main hover:bg-slate-100 dark:hover:bg-slate-800'
                }`}
              >
                {chip.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Trust Lens */}
      <TrustLens
        mode={trustMode}
        onChange={setTrustMode}
        totalCount={timelineItems?.length || 0}
        filteredCount={filteredItems.length}
      />

      {/* Timeline Stream */}
      {isLoading ? (
        <div className="p-12 text-center text-text-muted animate-pulse">Loading timeline milestones...</div>
      ) : Object.keys(groupedByMonth).length === 0 ? (
        <Card className="p-12 text-center text-text-muted">
          <Clock className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p className="text-sm font-medium text-text-main">No timeline entries found for the selected filter.</p>
        </Card>
      ) : (
        <div className="space-y-8">
          {Object.entries(groupedByMonth).map(([month, items]) => (
            <div key={month} className="space-y-4">
              {/* Month Header Banner */}
              <div className="sticky top-0 z-10 flex items-center gap-3 bg-background/90 backdrop-blur-sm py-2">
                <span className="px-3 py-1 rounded-full bg-navy dark:bg-teal text-white text-xs font-semibold shadow-sm">
                  {month}
                </span>
                <div className="flex-1 h-px bg-border" />
                <span className="text-xs text-text-muted font-mono">{items.length} items</span>
              </div>

              {/* Vertical Timeline Items */}
              <div className="relative pl-6 border-l-2 border-border ml-4 space-y-4">
                {items.map((item) => {
                  const isAmber = item.is_unresolved;
                  return (
                    <div
                      key={item.id}
                      className={`relative p-4 rounded-card border transition-all ${
                        isAmber
                          ? 'bg-amber-50/40 dark:bg-amber-950/20 border-amber-300 dark:border-amber-700/60 shadow-sm'
                          : 'bg-surface border-border shadow-soft'
                      }`}
                    >
                      {/* Timeline Node Dot */}
                      <div
                        className={`absolute -left-[31px] top-4 w-3.5 h-3.5 rounded-full border-2 border-surface ${
                          isAmber ? 'bg-amber-500 ring-2 ring-amber-200 dark:ring-amber-900' : 'bg-navy dark:bg-teal ring-2 ring-border'
                        }`}
                      />

                      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-mono text-text-muted bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded border border-border">
                              {item.date}
                            </span>
                            <span className="text-xs font-semibold text-text-muted capitalize">
                              [{item.type.replace('_', ' ')}]
                            </span>
                            {item.is_unresolved && (
                              <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-700 dark:text-amber-300 bg-amber-100 dark:bg-amber-950/60 px-2 py-0.5 rounded border border-amber-300 dark:border-amber-800">
                                <AlertTriangle className="w-3 h-3" />
                                <span>Unresolved</span>
                              </span>
                            )}
                          </div>

                          <h3 className="text-sm font-semibold text-text-main mt-1">{item.title}</h3>

                          {item.evidence_snippet && (
                            <p className="text-xs font-mono text-text-main bg-slate-50 dark:bg-slate-800/40 p-2 rounded border border-border mt-2 line-clamp-2">
                              &quot;{item.evidence_snippet}&quot;
                            </p>
                          )}

                          <div className="flex items-center gap-2 text-xs text-text-muted pt-1">
                            {item.owner_name && (
                              <span>
                                Attribution: <strong className="text-text-main">{item.owner_name}</strong>
                              </span>
                            )}
                            {item.source_label && (
                              <>
                                <span>•</span>
                                <span className="font-mono text-[11px]">{item.source_label}</span>
                              </>
                            )}
                          </div>
                        </div>

                        {/* Status Badges & Evidence Button */}
                        <div className="flex sm:flex-col items-center sm:items-end justify-between sm:justify-start gap-2 flex-shrink-0">
                          <div className="flex items-center gap-1.5">
                            <StatusBadge status={item.status} size="sm" />
                            <ClearanceBadge clearance={item.clearance} size="sm" />
                          </div>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setSelectedClaimId(item.id)}
                            leftIcon={<Eye className="w-3.5 h-3.5" />}
                          >
                            View evidence
                          </Button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Evidence Drawer */}
      <EvidenceDrawer claimId={selectedClaimId} onClose={() => setSelectedClaimId(null)} />
    </div>
  );
};
