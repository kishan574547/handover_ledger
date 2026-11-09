import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ListChecks, User, Clock, Filter } from 'lucide-react';
import { api } from '../api/client';
import { ActivityItem } from '../types';
import { Card, CardHeader, CardTitle, CardContent } from '../components/common/Card';
import { TableRowSkeleton } from '../components/common/Skeleton';

export const ActivityPage: React.FC = () => {
  const [selectedRole, setSelectedRole] = useState<string>('');

  const { data: logs, isLoading } = useQuery<ActivityItem[]>({
    queryKey: ['activity-logs', selectedRole],
    queryFn: () => api.getActivityLogs(selectedRole || undefined),
    staleTime: 5000,
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Audit & Activity Log</h2>
          <p className="text-sm text-slate-500 mt-1">
            Immutable log of all user and system operations: analysis runs, reviews, conflict resolutions, and acknowledgements.
          </p>
        </div>

        {/* Role Filter */}
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-slate-400" />
          <select
            value={selectedRole}
            onChange={(e) => setSelectedRole(e.target.value)}
            className="text-xs py-2 px-3 border border-slate-300 rounded-lg bg-white text-slate-700"
          >
            <option value="">All Roles</option>
            <option value="lead">Project Lead</option>
            <option value="departing">Departing Member</option>
            <option value="developer">Successor Developer</option>
            <option value="coordinator">Coordinator</option>
          </select>
        </div>
      </div>

      {/* Activity Table */}
      <Card>
        <CardContent className="p-0 overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-[11px] font-semibold text-slate-600 uppercase tracking-wider">
                <th className="py-3 px-5">Timestamp</th>
                <th className="py-3 px-4">Role</th>
                <th className="py-3 px-4">Action</th>
                <th className="py-3 px-5">Target / Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                Array.from({ length: 6 }).map((_, i) => <TableRowSkeleton key={i} cols={4} />)
              ) : !logs || logs.length === 0 ? (
                <tr>
                  <td colSpan={4} className="py-12 text-center text-slate-400">
                    <ListChecks className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    <p className="text-sm font-medium text-slate-600">No activity logged yet.</p>
                  </td>
                </tr>
              ) : (
                logs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-50">
                    <td className="py-3 px-5 font-mono text-slate-500 whitespace-nowrap">
                      {new Date(log.at).toLocaleString([], { dateStyle: 'short', timeStyle: 'medium' })}
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      <span className="font-semibold text-slate-800 capitalize bg-slate-100 px-2 py-0.5 rounded">
                        {log.role}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono font-medium text-navy whitespace-nowrap">
                      {log.action}
                    </td>
                    <td className="py-3 px-5 text-slate-700 font-medium">
                      {log.target}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
};

