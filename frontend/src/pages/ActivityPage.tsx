import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ListChecks, User, Clock, Filter, Shield } from 'lucide-react';
import { api } from '../api/client';
import { ActivityItem } from '../types';
import { Card, CardHeader, CardTitle, CardContent } from '../components/common/Card';
import { TableRowSkeleton } from '../components/common/Skeleton';
import { formatLocalDateTime } from '../utils/date';

export const ActivityPage: React.FC = () => {
  const [selectedRole, setSelectedRole] = useState<string>('');

  const { data: logs, isLoading } = useQuery<ActivityItem[]>({
    queryKey: ['activity-logs', selectedRole],
    queryFn: () => api.getActivityLogs(selectedRole || undefined),
    staleTime: 5000,
  });

  return (
    <div className="space-y-6">
      {/* Standard Page Header Pattern */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6">
        <div>
          <h2 className="page-title text-text-main">Audit &amp; Activity Log</h2>
          <p className="text-sm text-text-muted mt-1">
            Immutable log of all user and system operations: analysis runs, reviews, conflict resolutions, and acknowledgements.
          </p>
        </div>

        {/* Role Filter */}
        <div className="flex items-center gap-2 self-start sm:self-auto">
          <Filter className="w-4 h-4 text-text-muted" />
          <select
            value={selectedRole}
            onChange={(e) => setSelectedRole(e.target.value)}
            className="text-xs py-2 px-3 border border-border rounded-btn bg-surface text-text-main shadow-sm focus:ring-1 focus:ring-navy focus:outline-none min-h-[40px]"
            aria-label="Filter activity by role"
          >
            <option value="">All Roles</option>
            <option value="lead">Project Lead</option>
            <option value="departing">Departing Member</option>
            <option value="developer">Successor Developer</option>
            <option value="coordinator">Coordinator</option>
          </select>
        </div>
      </div>

      {/* Activity Card Container */}
      <Card>
        <CardContent className="p-0">
          {/* Mobile Stacked Cards (< 768px) */}
          <div className="md:hidden divide-y divide-border">
            {isLoading ? (
              Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="p-4 space-y-2 animate-pulse">
                  <div className="h-4 bg-slate-200 dark:bg-slate-700 w-1/3 rounded" />
                  <div className="h-4 bg-slate-200 dark:bg-slate-700 w-3/4 rounded" />
                </div>
              ))
            ) : !logs || logs.length === 0 ? (
              <div className="py-12 text-center text-text-muted">
                <ListChecks className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm font-medium text-text-main">No activity logged yet.</p>
                <p className="text-xs text-text-muted mt-1">Operations like analysis runs and approvals will appear here.</p>
              </div>
            ) : (
              logs.map((log) => (
                <div key={log.id} className="p-4 space-y-2 hover:bg-slate-50/50 dark:hover:bg-slate-800/40 transition-colors">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-semibold text-xs text-text-main capitalize bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded border border-border">
                      {log.role}
                    </span>
                    <span
                      className="font-mono text-[11px] text-text-muted"
                      title={new Date(log.at).toLocaleString()}
                    >
                      {new Date(log.at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}
                    </span>
                  </div>
                  <div className="text-xs font-mono font-medium text-navy dark:text-teal">
                    {log.action}
                  </div>
                  <p className="text-xs text-text-main leading-relaxed">
                    {log.target}
                  </p>
                </div>
              ))
            )}
          </div>

          {/* Desktop Table (>= 768px) */}
          <div className="hidden md:block overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="sticky top-0 bg-surface z-10 border-b border-border text-[11px] font-semibold text-text-muted uppercase tracking-wider">
                  <th className="py-3 px-5">Timestamp</th>
                  <th className="py-3 px-4">Role</th>
                  <th className="py-3 px-4">Action</th>
                  <th className="py-3 px-5">Target / Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {isLoading ? (
                  Array.from({ length: 6 }).map((_, i) => <TableRowSkeleton key={i} cols={4} />)
                ) : !logs || logs.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="py-12 text-center text-text-muted">
                      <ListChecks className="w-8 h-8 mx-auto mb-2 opacity-50" />
                      <p className="text-sm font-medium text-text-main">No activity logged yet.</p>
                      <p className="text-xs text-text-muted mt-1">Operations like analysis runs and approvals will appear here.</p>
                    </td>
                  </tr>
                ) : (
                  logs.map((log) => (
                    <tr key={log.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition-colors">
                      <td
                        className="py-3 px-5 font-mono text-text-muted whitespace-nowrap cursor-help"
                        title={formatLocalDateTime(log.at).iso}
                      >
                        {formatLocalDateTime(log.at).display}
                      </td>
                      <td className="py-3 px-4 whitespace-nowrap">
                        <span className="font-semibold text-text-main capitalize bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded border border-border">
                          {log.role}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-mono font-medium text-navy dark:text-teal whitespace-nowrap">
                        {log.action}
                      </td>
                      <td className="py-3 px-5 text-text-main font-medium">
                        {log.target}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
