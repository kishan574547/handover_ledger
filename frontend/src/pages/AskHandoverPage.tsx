import React, { useState, useEffect, useRef } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  MessageSquareQuote,
  Send,
  Sparkles,
  ShieldCheck,
  AlertTriangle,
  Copy,
  Check,
  UserPlus,
  ArrowRight,
  ExternalLink,
  Lock,
  Layers,
  HelpCircle,
  RefreshCw,
} from 'lucide-react';
import { api } from '../api/client';
import { useRole } from '../context/RoleContext';
import { useToast } from '../context/ToastContext';
import { AskResponseData, ClaimItem, DashboardData } from '../types';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Drawer } from '../components/common/Drawer';
import { StatusBadge, ClearanceBadge } from '../components/common/Badge';
import { Skeleton } from '../components/common/Skeleton';
import { recordGuideStep } from '../components/common/JudgeGuide';

export const AskHandoverPage: React.FC = () => {
  const { role, canLead } = useRole();
  const { success, error, info } = useToast();
  const queryClient = useQueryClient();

  useEffect(() => {
    document.title = 'Ask the Handover | HandoverLedger';
  }, []);

  const [activeTab, setActiveTab] = useState<'handover' | 'help'>('handover');
  const [question, setQuestion] = useState('');
  const [helpQuestion, setHelpQuestion] = useState('');
  const [history, setHistory] = useState<
    { q: string; response?: AskResponseData; error?: string; loading?: boolean }[]
  >([]);
  const [helpHistory, setHelpHistory] = useState<
    { q: string; answer?: string; suggestedSteps?: string[]; error?: string; loading?: boolean }[]
  >([]);
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);

  // Evidence drawer state for clicked citations
  const [selectedClaimId, setSelectedClaimId] = useState<string | null>(null);
  const [selectedClaim, setSelectedClaim] = useState<any | null>(null);
  const [isEvidenceDrawerOpen, setIsEvidenceDrawerOpen] = useState(false);

  const { data: dashboardData } = useQuery<DashboardData>({
    queryKey: ['dashboard'],
    queryFn: api.getDashboard,
  });

  const starterChips = React.useMemo(() => {
    const chips: { label: string; q: string }[] = [];
    chips.push({ label: 'First Week Priorities', q: 'What should I focus on during my first week?' });
    chips.push({ label: 'Biggest Risks', q: 'What are the biggest risks I should be aware of?' });

    if (dashboardData?.top_risks && dashboardData.top_risks.length > 0) {
      const topRisk = dashboardData.top_risks[0];
      const riskSubject = (topRisk?.subject_key || '').replace(/_/g, ' ');
      if (riskSubject && !['payment_gateway', 'razorpay', 'campus', 'demo'].some(d => riskSubject.toLowerCase().includes(d))) {
        chips.push({ label: `Risk: ${riskSubject}`, q: `What is the risk related to ${riskSubject}?` });
      }
    }

    if (dashboardData?.next_actions && dashboardData.next_actions.length > 0) {
      chips.push({ label: 'Open Actions', q: 'Are there stalled items or open blockers?' });
    }

    chips.push({ label: 'Ownership Map', q: 'Who owns what in this project?' });

    return chips.slice(0, 4);
  }, [dashboardData]);

  const helpStarterChips = [
    { label: 'Clearances & Roles', q: 'What are the 3 clearance levels and what does each role see?' },
    { label: 'Dual-Check Verification', q: 'How does evidence verification enforce verbatim quotes (>= 90%)?' },
    { label: 'Leak Check Security', q: 'How does the Pre-Export Leak Check block credential and clearance leaks?' },
    { label: 'Analysis Pipeline', q: 'What are the 6 stages of the automated analysis pipeline?' },
  ];

  // Ask Mutation (Grounded Handover Q&A)
  const askMutation = useMutation({
    mutationFn: (qText: string) => api.askHandover(qText),
    onSuccess: (data: AskResponseData, variables) => {
      setHistory((prev) =>
        prev.map((item) =>
          item.q === variables ? { ...item, response: data, loading: false } : item
        )
      );
      recordGuideStep('ask_handover');
    },
    onError: (err: any, variables) => {
      setHistory((prev) =>
        prev.map((item) =>
          item.q === variables ? { ...item, error: err.message, loading: false } : item
        )
      );
      error('Q&A Error', err.message);
    },
  });

  // Help Mutation (How to Use This App)
  const helpMutation = useMutation({
    mutationFn: (qText: string) => api.askHelp(qText),
    onSuccess: (data, variables) => {
      setHelpHistory((prev) =>
        prev.map((item) =>
          item.q === variables
            ? { ...item, answer: data.answer, suggestedSteps: data.suggested_steps, loading: false }
            : item
        )
      );
    },
    onError: (err: any, variables) => {
      setHelpHistory((prev) =>
        prev.map((item) =>
          item.q === variables ? { ...item, error: err.message, loading: false } : item
        )
      );
      error('Guide Error', err.message);
    },
  });

  // Send to Leaver Mutation
  const sendToLeaverMutation = useMutation({
    mutationFn: (qText: string) => api.sendQuestionToLeaver(qText),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['questions'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      success('Question Sent', 'Targeted knowledge gap question added to the leaver’s Exit Interview.');
      recordGuideStep('answer_question');
    },
    onError: (err: any) => error('Submission Failed', err.message),
  });

  const handleAsk = (qText: string) => {
    const text = qText.trim();
    if (!text || askMutation.isPending) return;

    setQuestion('');
    setHistory((prev) => [...prev, { q: text, loading: true }]);
    askMutation.mutate(text);
  };

  const handleCopy = (text: string, idx: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 2000);
    success('Copied', 'Answer text copied to clipboard.');
  };

  const handleOpenCitation = async (claimId: string) => {
    try {
      const claim = await api.getClaimDetail(claimId);
      setSelectedClaim(claim);
      setSelectedClaimId(claimId);
      setIsEvidenceDrawerOpen(true);
      recordGuideStep('open_evidence');
    } catch (err: any) {
      error('Error', 'Could not fetch claim evidence.');
    }
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Page Header */}
      <div>
        <div className="flex items-center gap-2">
          <h2 className="page-title text-text-main">
            {activeTab === 'handover' ? 'Ask the Handover' : 'How to Use This App'}
          </h2>
          <span className="px-2 py-0.5 rounded-full bg-teal/10 text-teal text-xs font-semibold">
            {activeTab === 'handover' ? 'Strictly Grounded Q&A' : 'AI User Guide'}
          </span>
        </div>
        <p className="text-sm text-text-muted mt-1 leading-relaxed">
          {activeTab === 'handover'
            ? `Ask questions in natural language. Answers are grounded strictly on approved claims within your role's clearance (${role}). Every sentence includes exact citations.`
            : 'Interactive user guide for HandoverLedger. Ask anything about clearances, verification rules, roles, leak checks, or features.'}
        </p>

        {/* Tab Switcher */}
        <div className="flex items-center gap-1.5 mt-4 p-1 bg-bg-surface border border-border-subtle rounded-lg w-fit">
          <button
            onClick={() => setActiveTab('handover')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
              activeTab === 'handover'
                ? 'bg-navy dark:bg-teal text-white dark:text-slate-900 shadow-sm'
                : 'text-text-muted hover:text-text-main'
            }`}
          >
            Ask the Handover
          </button>
          <button
            onClick={() => setActiveTab('help')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all flex items-center gap-1.5 ${
              activeTab === 'help'
                ? 'bg-navy dark:bg-teal text-white dark:text-slate-900 shadow-sm'
                : 'text-text-muted hover:text-text-main'
            }`}
          >
            <HelpCircle className="w-3.5 h-3.5" />
            <span>How to use this app</span>
          </button>
        </div>
      </div>

      {activeTab === 'handover' ? (
        <>
          {/* Starter Suggestions */}
          <div>
            <label className="text-xs font-semibold text-text-muted uppercase tracking-wider block mb-2">
              Recommended Questions
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {starterChips.map((chip, idx) => (
                <button
                  key={idx}
                  onClick={() => handleAsk(chip.q)}
                  disabled={askMutation.isPending}
                  className="p-3 rounded-card border border-border bg-surface hover:border-slate-300 dark:hover:border-slate-700 text-left transition-all text-xs flex items-center justify-between gap-2 group min-h-[44px]"
                >
                  <div>
                    <span className="font-semibold text-navy dark:text-teal block">{chip.label}</span>
                    <span className="text-text-muted mt-0.5 block truncate max-w-xs">{chip.q}</span>
                  </div>
                  <ArrowRight className="w-4 h-4 text-text-muted group-hover:text-text-main flex-shrink-0 transition-transform group-hover:translate-x-0.5" />
                </button>
              ))}
            </div>
          </div>

      {/* Question Input Card */}
      <Card>
        <CardContent className="p-3 sm:p-4">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleAsk(question);
            }}
            className="flex flex-col sm:flex-row gap-2"
          >
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="e.g., What is the API timeout decision and why was it chosen?"
              className="flex-1 bg-surface border border-border rounded-btn px-4 py-2.5 text-sm text-text-main placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-navy dark:focus:ring-teal min-h-[44px]"
            />
            <Button
              type="submit"
              variant="primary"
              disabled={!question.trim() || askMutation.isPending}
              isLoading={askMutation.isPending}
              leftIcon={<Send className="w-4 h-4" />}
            >
              Ask
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Q&A Thread History */}
      <div className="space-y-4">
        {history.map((item, idx) => (
          <Card key={idx} className="overflow-hidden">
            {/* User Question */}
            <div className="p-4 bg-slate-50 dark:bg-slate-900/50 border-b border-border flex items-start gap-3">
              <div className="w-7 h-7 rounded-full bg-navy/10 dark:bg-teal/20 text-navy dark:text-teal flex items-center justify-center font-bold text-xs flex-shrink-0 mt-0.5">
                Q
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-text-main">{item.q}</p>
              </div>
            </div>

            {/* Answer Content */}
            <div className="p-4 sm:p-5 space-y-4">
              {item.loading && (
                <div className="space-y-2">
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-4 w-5/6" />
                  <Skeleton className="h-4 w-1/2" />
                </div>
              )}

              {item.error && (
                <div className="p-3 rounded-btn bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-xs text-rose-700 dark:text-rose-300">
                  {item.error}
                </div>
              )}

              {item.response && (
                <>
                  {/* Found Status Banner */}
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <span
                      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${
                        item.response.found
                          ? item.response.verification_summary === 'Backed by verified evidence'
                            ? 'bg-status-verified-bg text-status-verified-text border border-status-verified-border'
                            : 'bg-status-inferred-bg text-status-inferred-text border border-status-inferred-border'
                          : 'bg-slate-100 dark:bg-slate-800 text-text-muted border border-border'
                      }`}
                    >
                      {item.response.found ? (
                        <ShieldCheck className="w-3.5 h-3.5" />
                      ) : (
                        <HelpCircle className="w-3.5 h-3.5" />
                      )}
                      <span>{item.response.verification_summary}</span>
                    </span>

                    <button
                      onClick={() => handleCopy(item.response?.answer || '', idx)}
                      className="text-xs text-text-muted hover:text-text-main flex items-center gap-1.5 p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800"
                    >
                      {copiedIdx === idx ? (
                        <>
                          <Check className="w-3.5 h-3.5 text-emerald-600" />
                          <span className="text-emerald-600">Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3.5 h-3.5" />
                          <span>Copy Answer</span>
                        </>
                      )}
                    </button>
                  </div>

                  {/* Grounded Sentences with Citations */}
                  <div className="text-sm text-text-main leading-relaxed space-y-2">
                    {item.response.sentences && item.response.sentences.length > 0 ? (
                      item.response.sentences.map((sent, sIdx) => (
                        <p key={sIdx} className="inline">
                          <span>{sent.text} </span>
                          <span className="inline-flex items-center gap-1">
                            {sent.claim_ids.map((cid) => (
                              <button
                                key={cid}
                                onClick={() => handleOpenCitation(cid)}
                                className="inline-flex items-center px-1.5 py-0.5 text-[11px] font-mono rounded bg-navy/10 hover:bg-navy/20 dark:bg-teal/20 dark:hover:bg-teal/30 text-navy dark:text-teal transition-colors font-medium ml-1"
                                title="Click to view verbatim evidence"
                              >
                                [#{cid.slice(0, 6)}]
                              </button>
                            ))}
                          </span>{' '}
                        </p>
                      ))
                    ) : (
                      <p className="text-text-muted italic">{item.response.answer}</p>
                    )}
                  </div>

                  {/* Restricted Information Notice */}
                  {item.response.restricted_notice && (
                    <div className="p-3 rounded-btn bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 text-xs text-amber-800 dark:text-amber-200 flex items-center gap-2">
                      <Lock className="w-4 h-4 flex-shrink-0" />
                      <span>{item.response.restricted_notice}</span>
                    </div>
                  )}

                  {/* Not Found: distinct message per reason_code */}
                  {!item.response.found && (
                    <div className="pt-2 border-t border-border space-y-2">
                      {item.response.reason_code === 'no_approved_claims' ? (
                        <div className="flex items-center gap-2 text-xs text-amber-700 dark:text-amber-300">
                          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                          <span>{item.response.answer}</span>
                        </div>
                      ) : item.response.reason_code === 'ai_error' ? (
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-xs text-rose-600 dark:text-rose-400 flex items-center gap-1.5">
                            <AlertTriangle className="w-3.5 h-3.5" />
                            {item.response.answer}
                          </span>
                          <Button variant="secondary" size="sm" onClick={() => handleAsk(item.q)} leftIcon={<RefreshCw className="w-3 h-3" />}>Retry</Button>
                        </div>
                      ) : item.response.reason_code === 'not_found' ? (
                        <div className="flex items-center justify-between flex-wrap gap-2">
                          <p className="text-xs text-text-muted">This information is missing from the handover ledger.</p>
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => sendToLeaverMutation.mutate(item.q)}
                            isLoading={sendToLeaverMutation.isPending}
                            leftIcon={<UserPlus className="w-3.5 h-3.5" />}
                          >
                            Send this question to the leaver
                          </Button>
                        </div>
                      ) : null}
                    </div>
                  )}

                  {/* Citations List Drawer Trigger */}
                  {item.response.cited_claims && item.response.cited_claims.length > 0 && (
                    <div className="pt-3 border-t border-border space-y-1.5">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-text-muted block">
                        Cited Evidence Claims ({item.response.cited_claims.length})
                      </span>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {item.response.cited_claims.map((c) => (
                          <button
                            key={c.id}
                            onClick={() => handleOpenCitation(c.id)}
                            className="p-2.5 rounded-btn border border-border bg-surface hover:border-slate-300 dark:hover:border-slate-700 text-left transition-all text-xs flex items-start gap-2"
                          >
                            <StatusBadge status={c.status} size="sm" />
                            <div className="flex-1 min-w-0">
                              <span className="font-mono text-[10px] text-text-muted block truncate">
                                #{c.id.slice(0, 8)}
                              </span>
                              <p className="text-[11px] text-text-main line-clamp-1 mt-0.5">
                                {c.short_text}
                              </p>
                            </div>
                            <ExternalLink className="w-3.5 h-3.5 text-text-muted flex-shrink-0" />
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Transparency: How this was answered */}
                  {((item.response.claims_considered ?? 0) > 0 || Boolean(item.response.model_used)) && (
                    <details className="pt-2 border-t border-border">
                      <summary className="text-[10px] text-text-muted cursor-pointer hover:text-text-main flex items-center gap-1 select-none">
                        <Layers className="w-3 h-3" />
                        How this was answered
                      </summary>
                      <div className="mt-1.5 text-[11px] text-text-muted space-y-0.5 pl-4">
                        {(item.response.claims_considered ?? 0) > 0 && (
                          <p>Claims considered: {item.response.claims_considered} · Claims cited: {item.response.claims_cited}</p>
                        )}
                        {item.response.model_used && (
                          <p>Model: {item.response.model_used}{item.response.from_cache ? ' · (cached response)' : ''}</p>
                        )}
                      </div>
                    </details>
                  )}
                </>
              )}
            </div>
          </Card>
        ))}
      </div>
        </>
      ) : (
        /* How to Use This App Guide Tab */
        <div className="space-y-6">
          {/* Guide Starter Chips */}
          <div>
            <label className="text-xs font-semibold text-text-muted uppercase tracking-wider block mb-2">
              Common App Questions
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {helpStarterChips.map((chip, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    setHelpHistory((prev) => [...prev, { q: chip.q, loading: true }]);
                    helpMutation.mutate(chip.q);
                  }}
                  disabled={helpMutation.isPending}
                  className="p-3 rounded-card border border-border bg-surface hover:border-slate-300 dark:hover:border-slate-700 text-left transition-all text-xs flex items-center justify-between gap-2 group min-h-[44px]"
                >
                  <div>
                    <span className="font-semibold text-navy dark:text-teal block">{chip.label}</span>
                    <span className="text-text-muted mt-0.5 block truncate max-w-xs">{chip.q}</span>
                  </div>
                  <ArrowRight className="w-4 h-4 text-text-muted group-hover:text-text-main flex-shrink-0 transition-transform group-hover:translate-x-0.5" />
                </button>
              ))}
            </div>
          </div>

          {/* Guide Question Input */}
          <Card>
            <CardContent className="p-3 sm:p-4">
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  if (!helpQuestion.trim() || helpMutation.isPending) return;
                  const q = helpQuestion.trim();
                  setHelpQuestion('');
                  setHelpHistory((prev) => [...prev, { q, loading: true }]);
                  helpMutation.mutate(q);
                }}
                className="flex flex-col sm:flex-row gap-2"
              >
                <input
                  type="text"
                  value={helpQuestion}
                  onChange={(e) => setHelpQuestion(e.target.value)}
                  placeholder="Ask anything about using HandoverLedger, clearances, or features..."
                  className="flex-1 bg-surface border border-border rounded-btn px-4 py-2.5 text-sm text-text-main placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-navy dark:focus:ring-teal min-h-[44px]"
                />
                <Button
                  type="submit"
                  variant="primary"
                  disabled={!helpQuestion.trim() || helpMutation.isPending}
                  isLoading={helpMutation.isPending}
                  leftIcon={<Send className="w-4 h-4" />}
                >
                  Ask Guide
                </Button>
              </form>
            </CardContent>
          </Card>

          {/* Guide History */}
          <div className="space-y-4">
            {helpHistory.map((item, idx) => (
              <Card key={idx} className="overflow-hidden">
                <CardHeader className="bg-slate-50 dark:bg-slate-900/50 border-b border-border py-3 px-4">
                  <div className="flex items-center gap-2">
                    <HelpCircle className="w-4 h-4 text-teal" />
                    <span className="font-semibold text-sm text-text-main">{item.q}</span>
                  </div>
                </CardHeader>
                <CardContent className="p-4 space-y-3">
                  {item.loading && (
                    <div className="space-y-2 py-2">
                      <Skeleton className="h-4 w-full" />
                      <Skeleton className="h-4 w-4/5" />
                    </div>
                  )}

                  {item.error && (
                    <div className="p-3 rounded-card bg-rose-50 border border-rose-200 text-xs text-rose-800">
                      {item.error}
                    </div>
                  )}

                  {item.answer && (
                    <>
                      <p className="text-sm text-text-main leading-relaxed">
                        {item.answer}
                      </p>

                      {item.suggestedSteps && item.suggestedSteps.length > 0 && (
                        <div className="pt-2 border-t border-border-subtle">
                          <label className="text-[11px] font-semibold text-text-muted block mb-1.5">
                            Recommended Next Steps:
                          </label>
                          <div className="flex flex-wrap gap-1.5">
                            {item.suggestedSteps.map((step, sIdx) => (
                              <span
                                key={sIdx}
                                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs bg-slate-100 dark:bg-slate-800 text-text-main border border-border"
                              >
                                <ArrowRight className="w-3 h-3 text-teal" />
                                <span>{step}</span>
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Evidence Drawer */}
      <Drawer
        isOpen={isEvidenceDrawerOpen}
        onClose={() => setIsEvidenceDrawerOpen(false)}
        title={selectedClaim ? `Claim #${selectedClaim.id.slice(0, 8)}` : 'Evidence Details'}
        subtitle={selectedClaim?.subject_key}
      >
        {selectedClaim && (
          <div className="space-y-4 text-xs">
            <div className="flex items-center gap-2">
              <StatusBadge status={selectedClaim.status} />
              <ClearanceBadge clearance={selectedClaim.clearance} />
            </div>

            <div>
              <label className="text-[10px] font-bold uppercase text-text-muted block mb-1">
                Claim Statement
              </label>
              <p className="text-sm font-medium text-text-main bg-slate-50 dark:bg-slate-900/40 p-3 rounded-card border border-border">
                {selectedClaim.text}
              </p>
            </div>

            {selectedClaim.evidence && selectedClaim.evidence.length > 0 && (
              <div className="space-y-2">
                <label className="text-[10px] font-bold uppercase text-text-muted block">
                  Verbatim Passage Citations
                </label>
                {selectedClaim.evidence.map((ev: any, idx: number) => (
                  <div key={idx} className="p-3 rounded-card border border-border bg-surface space-y-1.5">
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="font-semibold text-text-main">{ev.source_name || 'Source'}</span>
                      <span className="font-mono text-teal">Match: {ev.match_score}%</span>
                    </div>
                    <blockquote className="p-2.5 rounded bg-slate-100 dark:bg-slate-800 font-mono text-[11px] text-text-main border-l-2 border-teal">
                      &quot;{ev.quote}&quot;
                    </blockquote>
                    {ev.reason && (
                      <p className="text-[10px] text-text-muted italic">{ev.reason}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </Drawer>
    </div>
  );
};

