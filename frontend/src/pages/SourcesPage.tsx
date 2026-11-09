import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Database,
  Github,
  FileText,
  MessageSquare,
  Upload,
  Shield,
  Trash2,
  Lock,
  Play,
  CheckCircle2,
  AlertCircle,
  Clock,
  Sparkles,
  Info,
  X,
} from 'lucide-react';
import { api } from '../api/client';
import { SourceItem, AnalysisStatusData } from '../types';
import { useRole } from '../context/RoleContext';
import { useToast } from '../context/ToastContext';
import { Card, CardHeader, CardTitle, CardContent } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Modal } from '../components/common/Modal';
import { Stepper } from '../components/common/Stepper';
import { TableRowSkeleton } from '../components/common/Skeleton';

export const SourcesPage: React.FC = () => {
  const navigate = useNavigate();
  const { canLead, role } = useRole();
  const { success, error } = useToast();
  const queryClient = useQueryClient();

  // Modals state
  const [showGithubModal, setShowGithubModal] = useState(false);
  const [githubUrl, setGithubUrl] = useState('');
  const [githubError, setGithubError] = useState<string | null>(null);

  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploadKind, setUploadKind] = useState<'notes' | 'chat'>('notes');
  const [uploadClearance, setUploadClearance] = useState<number>(1);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const [deleteSourceId, setDeleteSourceId] = useState<string | null>(null);

  // Analysis Progress Panel
  const [isAnalysisModalOpen, setIsAnalysisModalOpen] = useState(false);
  const [isPollingAnalysis, setIsPollingAnalysis] = useState(false);

  // Fetch sources
  const { data: sources, isLoading } = useQuery<SourceItem[]>({
    queryKey: ['sources'],
    queryFn: api.getSources,
  });

  // Analysis status polling
  const { data: analysisStatus } = useQuery<AnalysisStatusData>({
    queryKey: ['analysis-status'],
    queryFn: api.getAnalysisStatus,
    enabled: isPollingAnalysis || isAnalysisModalOpen,
    refetchInterval: isPollingAnalysis ? 1500 : false,
  });

  useEffect(() => {
    if (analysisStatus?.is_running) {
      setIsPollingAnalysis(true);
    } else if (isPollingAnalysis && !analysisStatus?.is_running) {
      setIsPollingAnalysis(false);
      queryClient.invalidateQueries({ queryKey: ['sources'] });
      queryClient.invalidateQueries({ queryKey: ['claims'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      if (!analysisStatus?.error) {
        success('Analysis Complete', 'All sources processed, claims extracted and verified.');
      }
    }
  }, [analysisStatus, isPollingAnalysis, queryClient, success]);

  // Mutations
  const loadDemoMutation = useMutation({
    mutationFn: api.loadDemo,
    onSuccess: () => {
      queryClient.invalidateQueries();
      success('Demo Loaded', 'Loaded Campus Connect repository and synthetic sources.');
    },
    onError: (err: any) => error('Load Failed', err.message),
  });

  const addGithubMutation = useMutation({
    mutationFn: (url: string) => api.addGithubSource(url),
    onSuccess: (newSrc) => {
      queryClient.invalidateQueries({ queryKey: ['sources'] });
      setShowGithubModal(false);
      setGithubUrl('');
      setGithubError(null);
      success('Repository Added', `Imported ${newSrc.item_count} items from GitHub.`);
    },
    onError: (err: any) => {
      setGithubError(err.message);
    },
  });

  const uploadSourceMutation = useMutation({
    mutationFn: (formData: FormData) => api.uploadSource(formData),
    onSuccess: (newSrc) => {
      queryClient.invalidateQueries({ queryKey: ['sources'] });
      setShowUploadModal(false);
      setSelectedFile(null);
      success('Source Uploaded', `Parsed ${newSrc.item_count} chunks from ${newSrc.name}.`);
    },
    onError: (err: any) => error('Upload Failed', err.message),
  });

  const updateClearanceMutation = useMutation({
    mutationFn: ({ id, clearance }: { id: string; clearance: number }) =>
      api.updateSourceClearance(id, clearance),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sources'] });
      queryClient.invalidateQueries({ queryKey: ['claims'] });
      success('Clearance Updated', 'Source clearance and linked claims updated.');
    },
    onError: (err: any) => error('Update Failed', err.message),
  });

  const deleteSourceMutation = useMutation({
    mutationFn: (id: string) => api.deleteSource(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sources'] });
      setDeleteSourceId(null);
      success('Source Removed', 'Source deleted.');
    },
    onError: (err: any) => error('Delete Failed', err.message),
  });

  const triggerAnalysisMutation = useMutation({
    mutationFn: api.triggerAnalysis,
    onSuccess: () => {
      setIsAnalysisModalOpen(true);
      setIsPollingAnalysis(true);
    },
    onError: (err: any) => error('Analysis Error', err.message),
  });

  const handleFileUploadSubmit = () => {
    if (!selectedFile) return;
    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('kind', uploadKind);
    formData.append('clearance', String(uploadClearance));
    uploadSourceMutation.mutate(formData);
  };

  const getSourceIcon = (kind: string) => {
    switch (kind) {
      case 'github':
        return <Github className="w-5 h-5 text-slate-900" />;
      case 'chat':
        return <MessageSquare className="w-5 h-5 text-emerald-600" />;
      default:
        return <FileText className="w-5 h-5 text-blue-600" />;
    }
  };

  const totalSourcesCount = sources?.length || 0;

  return (
    <div className="space-y-6 pb-24">
      {/* Page Header & Action Buttons */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Connected Project Sources</h2>
          <p className="text-sm text-slate-500 mt-1">
            Authorised inputs scanned for claims. Secrets and personal data are masked prior to AI processing.
          </p>
        </div>

        {canLead && (
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => loadDemoMutation.mutate()}
              isLoading={loadDemoMutation.isPending}
            >
              Load Demo Project
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setGithubError(null);
                setShowGithubModal(true);
              }}
              leftIcon={<Github className="w-4 h-4" />}
            >
              Add GitHub Repository
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                setUploadKind('notes');
                setShowUploadModal(true);
              }}
              leftIcon={<FileText className="w-4 h-4" />}
            >
              Upload Meeting Notes
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                setUploadKind('chat');
                setShowUploadModal(true);
              }}
              leftIcon={<MessageSquare className="w-4 h-4" />}
            >
              Upload Chat Export
            </Button>
          </div>
        )}
      </div>

      {/* Sources Table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold text-slate-900">
            Active Sources ({totalSourcesCount})
          </CardTitle>
          <span className="text-xs text-slate-500">
            Source Clearance determines maximum classification of extracted claims.
          </span>
        </CardHeader>
        <CardContent className="p-0 overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50/80 border-b border-slate-200 text-[11px] font-semibold text-slate-600 uppercase tracking-wider">
                <th className="py-3 px-5">Source Name</th>
                <th className="py-3 px-4">Item Count</th>
                <th className="py-3 px-4">Clearance Level</th>
                <th className="py-3 px-4">Masking Protection</th>
                <th className="py-3 px-4">Added Time</th>
                {canLead && <th className="py-3 px-5 text-right">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-sm">
              {isLoading ? (
                Array.from({ length: 4 }).map((_, i) => <TableRowSkeleton key={i} cols={6} />)
              ) : totalSourcesCount === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-400">
                    <Database className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    <p className="text-sm font-medium text-slate-600">No sources connected yet.</p>
                    <p className="text-xs text-slate-400 mt-1">Connect a GitHub repo or upload meeting notes to begin.</p>
                  </td>
                </tr>
              ) : (
                sources!.map((src) => (
                  <tr key={src.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3.5 px-5">
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-slate-100 flex-shrink-0">
                          {getSourceIcon(src.kind)}
                        </div>
                        <div>
                          <p className="font-semibold text-slate-900 leading-tight">{src.name}</p>
                          <span className="text-xs text-slate-500 uppercase tracking-wider font-mono">
                            Type: {src.kind}
                          </span>
                        </div>
                      </div>
                    </td>

                    <td className="py-3.5 px-4 font-mono text-xs text-slate-700">
                      {src.item_count} {src.kind === 'github' ? 'commits/issues' : 'chunks'}
                    </td>

                    <td className="py-3.5 px-4">
                      {canLead ? (
                        <select
                          value={src.clearance}
                          onChange={(e) =>
                            updateClearanceMutation.mutate({
                              id: src.id,
                              clearance: Number(e.target.value),
                            })
                          }
                          className="text-xs font-medium rounded-lg border border-slate-300 bg-white px-2.5 py-1 text-slate-800 shadow-sm focus:border-navy focus:outline-none"
                        >
                          <option value={1}>Level 1: General</option>
                          <option value={2}>Level 2: Technical</option>
                          <option value={3}>Level 3: Confidential</option>
                        </select>
                      ) : (
                        <span className="text-xs font-medium">
                          {src.clearance === 1 ? 'General (1)' : src.clearance === 2 ? 'Technical (2)' : 'Confidential (3)'}
                        </span>
                      )}
                    </td>

                    <td className="py-3.5 px-4">
                      {src.masked_count > 0 ? (
                        <span
                          className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-800 border border-amber-200"
                          title="Sensitive tokens automatically sanitized before AI pipeline: secrets, passwords, emails, phones"
                        >
                          <Shield className="w-3.5 h-3.5 text-amber-600" />
                          <span>{src.masked_count} secrets masked</span>
                        </span>
                      ) : (
                        <span className="text-xs text-slate-400 flex items-center gap-1">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                          <span>Clean / Sanitized</span>
                        </span>
                      )}
                    </td>

                    <td className="py-3.5 px-4 text-xs text-slate-500">
                      {new Date(src.added_at).toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                    </td>

                    {canLead && (
                      <td className="py-3.5 px-5 text-right">
                        <button
                          onClick={() => setDeleteSourceId(src.id)}
                          className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors"
                          title="Delete source"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    )}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </CardContent>
      </Card>

      {/* Sticky Bottom Bar with Primary "Run analysis" */}
      <div className="fixed bottom-0 left-60 right-0 bg-white border-t border-slate-200 p-4 px-8 shadow-xl flex items-center justify-between z-10">
        <div className="flex items-center gap-3 text-xs text-slate-600">
          <Info className="w-4 h-4 text-navy flex-shrink-0" />
          <span>
            {totalSourcesCount === 0
              ? 'Connect at least one source before running pipeline analysis.'
              : `Ready to analyze ${totalSourcesCount} connected source(s) through 6-stage AI pipeline.`}
          </span>
        </div>

        {canLead && (
          <Button
            variant="primary"
            size="md"
            disabled={totalSourcesCount === 0 || triggerAnalysisMutation.isPending}
            onClick={() => triggerAnalysisMutation.mutate()}
            isLoading={triggerAnalysisMutation.isPending || isPollingAnalysis}
            leftIcon={<Play className="w-4 h-4" />}
          >
            Run Analysis Pipeline
          </Button>
        )}
      </div>

      {/* GitHub Repository Modal */}
      <Modal
        isOpen={showGithubModal}
        onClose={() => setShowGithubModal(false)}
        title="Add Public GitHub Repository"
        description="Ingests README, recent commits (up to 100), issues, and pull requests."
        footer={
          <>
            <Button variant="outline" size="sm" onClick={() => setShowGithubModal(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              isLoading={addGithubMutation.isPending}
              onClick={() => {
                if (!githubUrl.trim()) {
                  setGithubError('Repository URL cannot be empty.');
                  return;
                }
                addGithubMutation.mutate(githubUrl.trim());
              }}
            >
              Validate & Add
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div>
            <label className="text-xs font-semibold text-slate-700 block mb-1">GitHub Repository URL</label>
            <input
              type="text"
              placeholder="https://github.com/owner/repository or owner/repository"
              value={githubUrl}
              onChange={(e) => {
                setGithubUrl(e.target.value);
                setGithubError(null);
              }}
              className="w-full text-sm p-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-navy focus:outline-none"
            />
            <p className="text-[11px] text-slate-400 mt-1">Example: https://github.com/campus-club/campus-connect</p>
          </div>

          {githubError && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-800 flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
              <span>{githubError}</span>
            </div>
          )}
        </div>
      </Modal>

      {/* Upload File Modal (Notes or Chat) */}
      <Modal
        isOpen={showUploadModal}
        onClose={() => setShowUploadModal(false)}
        title={uploadKind === 'notes' ? 'Upload Meeting Notes / Document' : 'Upload Chat Export'}
        description={
          uploadKind === 'notes'
            ? 'Accepts .md, .txt, or .pdf files. Automatically partitioned into ~8-line chunks.'
            : 'Accepts .txt (WhatsApp/Slack export) or .json files. Grouped into 5-8 message blocks.'
        }
        footer={
          <>
            <Button variant="outline" size="sm" onClick={() => setShowUploadModal(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              disabled={!selectedFile}
              isLoading={uploadSourceMutation.isPending}
              onClick={handleFileUploadSubmit}
            >
              Upload & Process
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div>
            <label className="text-xs font-semibold text-slate-700 block mb-1">Clearance Level</label>
            <select
              value={uploadClearance}
              onChange={(e) => setUploadClearance(Number(e.target.value))}
              className="w-full text-sm p-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-navy focus:outline-none"
            >
              <option value={1}>Level 1: General (All roles can view)</option>
              <option value={2}>Level 2: Technical (Developer & Lead)</option>
              <option value={3}>Level 3: Confidential (Lead Only)</option>
            </select>
          </div>

          {/* Drag and Drop Box */}
          <div className="border-2 border-dashed border-slate-300 rounded-xl p-6 text-center hover:bg-slate-50 transition-colors">
            <Upload className="w-8 h-8 text-slate-400 mx-auto mb-2" />
            <input
              type="file"
              accept={uploadKind === 'notes' ? '.md,.txt,.pdf' : '.txt,.json'}
              onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
              className="hidden"
              id="file-upload-input"
            />
            <label
              htmlFor="file-upload-input"
              className="cursor-pointer text-sm font-semibold text-navy hover:underline"
            >
              Click to select a file
            </label>
            <p className="text-xs text-slate-400 mt-1">
              {uploadKind === 'notes' ? 'Markdown (.md), Plain text (.txt), or PDF (.pdf)' : 'Text (.txt) or JSON (.json)'}
            </p>
            {selectedFile && (
              <div className="mt-3 p-2 bg-emerald-50 border border-emerald-200 rounded-lg text-xs font-semibold text-emerald-800">
                Selected: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
              </div>
            )}
          </div>
        </div>
      </Modal>

      {/* Delete Source Confirm Modal */}
      <Modal
        isOpen={!!deleteSourceId}
        onClose={() => setDeleteSourceId(null)}
        title="Remove Source?"
        description="This will remove the source and delete its associated chunks and evidence."
        footer={
          <>
            <Button variant="outline" size="sm" onClick={() => setDeleteSourceId(null)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              size="sm"
              isLoading={deleteSourceMutation.isPending}
              onClick={() => deleteSourceId && deleteSourceMutation.mutate(deleteSourceId)}
            >
              Remove Source
            </Button>
          </>
        }
      >
        <p className="text-sm text-slate-700">
          Are you sure you want to delete this source? This action cannot be undone.
        </p>
      </Modal>

      {/* Analysis Progress Stepper Modal */}
      <Modal
        isOpen={isAnalysisModalOpen}
        onClose={() => {
          if (!isPollingAnalysis) setIsAnalysisModalOpen(false);
        }}
        title="AI Analysis Pipeline Progress"
        description="Reconstructing factual claims, fuzzy-matching quotes with rapidfuzz, identifying conflicts and gaps."
        maxWidth="xl"
        footer={
          !isPollingAnalysis ? (
            <div className="w-full flex justify-between items-center">
              {analysisStatus?.error ? (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => triggerAnalysisMutation.mutate()}
                >
                  Try Again
                </Button>
              ) : (
                <div />
              )}
              <Button
                variant="primary"
                size="sm"
                onClick={() => {
                  setIsAnalysisModalOpen(false);
                  navigate('/ledger');
                }}
              >
                View Claim Ledger
              </Button>
            </div>
          ) : undefined
        }
      >
        <div className="space-y-4 py-2">
          {analysisStatus ? (
            <Stepper
              steps={analysisStatus.steps}
              currentPercent={analysisStatus.percent}
              overallStatus={analysisStatus.current_step}
            />
          ) : (
            <div className="text-center py-6">
              <Sparkles className="w-8 h-8 text-navy mx-auto animate-spin" />
              <p className="text-sm text-slate-500 mt-2">Initializing analysis pipeline...</p>
            </div>
          )}

          {analysisStatus?.error && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-800 flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
              <div>
                <strong className="block font-semibold">Analysis Pipeline Error:</strong>
                <span>{analysisStatus.error}</span>
              </div>
            </div>
          )}
        </div>
      </Modal>
    </div>
  );
};
