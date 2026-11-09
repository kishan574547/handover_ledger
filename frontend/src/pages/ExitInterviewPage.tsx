import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  HelpCircle,
  CheckCircle2,
  AlertCircle,
  Clock,
  Sparkles,
  UserCheck,
  Send,
  SkipForward,
  Info,
  Layers,
  Search,
} from 'lucide-react';
import { api } from '../api/client';
import { QuestionItem } from '../types';
import { useRole } from '../context/RoleContext';
import { useToast } from '../context/ToastContext';
import { useProjectMeta } from '../context/ProjectMetaContext';
import { Card, CardHeader, CardTitle, CardContent } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Tabs } from '../components/common/Tabs';

export const ExitInterviewPage: React.FC = () => {
  const { role, canAnswerInterview } = useRole();
  const { isDemo, leaverName } = useProjectMeta();
  const { success, error, info } = useToast();
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState<string>('all');
  const [selectedQuestionId, setSelectedQuestionId] = useState<string | null>(null);
  const [answerInput, setAnswerInput] = useState<string>('');

  // Fetch questions
  const { data: questions, isLoading } = useQuery<QuestionItem[]>({
    queryKey: ['questions'],
    queryFn: () => api.getQuestions(),
  });

  // Re-run gap detection mutation ("Find more gaps")
  const generateGapsMutation = useMutation({
    mutationFn: api.generateQuestions,
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['questions'] });
      queryClient.invalidateQueries({ queryKey: ['claims'] });
      success('Gap Detection Complete', `Analyzed sources and discovered ${res.new_questions_count} new gap question(s).`);
    },
    onError: (err: any) => error('Gap Scan Error', err.message),
  });

  // Answer question mutation
  const answerMutation = useMutation({
    mutationFn: ({ id, answer }: { id: string; answer: string }) =>
      api.answerQuestion(id, answer),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['questions'] });
      queryClient.invalidateQueries({ queryKey: ['claims'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      setAnswerInput('');
      success('Answer Recorded', 'Answer recorded as a "Leaver-attested" claim in the ledger.');
    },
    onError: (err: any) => error('Answer Failed', err.message),
  });

  // Skip question mutation
  const skipMutation = useMutation({
    mutationFn: (id: string) => api.skipQuestion(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['questions'] });
      info('Question Skipped', 'Question marked as skipped for now.');
    },
    onError: (err: any) => error('Skip Failed', err.message),
  });

  // Unknown question mutation
  const unknownMutation = useMutation({
    mutationFn: (id: string) => api.unknownQuestion(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['questions'] });
      queryClient.invalidateQueries({ queryKey: ['claims'] });
      success('Marked Unknown', 'Item recorded as unrecorded/unknown by departing member.');
    },
    onError: (err: any) => error('Action Failed', err.message),
  });

  const allQuestions = questions || [];
  const answeredCount = allQuestions.filter((q) => q.state === 'answered').length;
  const totalCount = allQuestions.length;
  const progressPercent = totalCount > 0 ? Math.round((answeredCount / totalCount) * 100) : 0;

  // Filtered by tab
  const filteredQuestions = allQuestions.filter((q) => {
    if (activeTab === 'all') return true;
    return q.state === activeTab;
  });

  // Currently active question
  const currentQuestion = allQuestions.find((q) => q.id === selectedQuestionId) || filteredQuestions[0] || null;

  return (
    <div className="space-y-6">
      {/* Standard Page Header Pattern */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6">
        <div>
          <h2 className="page-title text-text-main">Exit Interview</h2>
          <p className="text-sm text-text-muted mt-1">
            Targeted knowledge transfer capturing unrecorded decisions, unowned PRs, and undocumented dependencies.
          </p>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto">
          <span className="text-xs bg-slate-100 dark:bg-slate-800 text-text-muted border border-border px-3 py-1.5 rounded-full font-medium">
            {canAnswerInterview ? 'Authorized to Submit Answers' : 'Read-Only Mode for Incoming Roles'}
          </span>
        </div>
      </div>

      {/* Intro Overview Banner */}
      <div className="bg-gradient-to-r from-navy to-navy-light text-white p-5 sm:p-6 rounded-card shadow-sm space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-teal-300 font-semibold text-xs tracking-wider uppercase">
            <Sparkles className="w-4 h-4" />
            <span>Targeted Gap Discovery</span>
          </div>
          <span className="text-xs bg-white/10 px-3 py-1 rounded-full text-slate-200">
            {answeredCount} of {totalCount} completed ({progressPercent}%)
          </span>
        </div>
        <p className="text-xs text-slate-200 max-w-2xl leading-relaxed">
          The system automatically found unrecorded decisions, unowned PRs, stalled issues, and undocumented dependencies.
          Answers provided by the leaver are tagged <strong>&quot;Leaver-attested&quot;</strong> and recorded into the project ledger.
        </p>

        {/* Progress Bar */}
        <div className="pt-2 max-w-md">
          <div className="w-full h-2 bg-navy-dark/60 rounded-full overflow-hidden">
            <div
              className="h-full bg-teal transition-all duration-500 rounded-full"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>
      </div>

      {/* Main Responsive Grid Interface (Collapses to 1 column below 1024px) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column (5 cols): Questions List */}
        <div className="lg:col-span-5 space-y-4">
          <Card className="p-0 overflow-hidden">
            <div className="p-4 border-b border-border flex items-center justify-between">
              <h3 className="text-sm font-semibold text-text-main">Gap Questions</h3>
              {canAnswerInterview && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => generateGapsMutation.mutate()}
                  isLoading={generateGapsMutation.isPending}
                  leftIcon={<Sparkles className="w-3.5 h-3.5 text-teal" />}
                >
                  Find more gaps
                </Button>
              )}
            </div>

            {/* Filter Tabs */}
            <Tabs
              tabs={[
                { id: 'all', label: 'All', count: totalCount },
                { id: 'open', label: 'Open', count: allQuestions.filter((q) => q.state === 'open').length },
                { id: 'answered', label: 'Answered', count: answeredCount },
                { id: 'skipped', label: 'Skipped', count: allQuestions.filter((q) => q.state === 'skipped').length },
              ]}
              activeTab={activeTab}
              onChange={setActiveTab}
              className="px-4 bg-slate-50/50 dark:bg-slate-800/40"
            />

            {/* Question List Items */}
            <div className="divide-y divide-border max-h-[520px] overflow-y-auto">
              {isLoading ? (
                <div className="p-8 text-center text-text-muted">Loading interview questions...</div>
              ) : filteredQuestions.length === 0 ? (
                <div className="p-8 text-center text-text-muted text-xs">
                  No questions match this filter tab.
                </div>
              ) : (
                filteredQuestions.map((q) => {
                  const isSelected = currentQuestion?.id === q.id;
                  return (
                    <button
                      key={q.id}
                      onClick={() => {
                        setSelectedQuestionId(q.id);
                        setAnswerInput(q.answer || '');
                      }}
                      className={`w-full text-left p-4 transition-all flex items-start gap-3 min-h-[44px] ${
                        isSelected
                          ? 'bg-blue-50/60 dark:bg-blue-950/40 border-l-4 border-l-navy dark:border-l-teal'
                          : 'hover:bg-slate-50/60 dark:hover:bg-slate-800/40 border-l-4 border-l-transparent'
                      }`}
                    >
                      <div className="flex-shrink-0 mt-0.5">
                        {q.state === 'answered' ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                        ) : q.state === 'skipped' ? (
                          <SkipForward className="w-4 h-4 text-text-muted" />
                        ) : q.state === 'unknown' ? (
                          <HelpCircle className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                        ) : (
                          <AlertCircle className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                        )}
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2 mb-1">
                          <span
                            className={`text-[10px] font-semibold uppercase px-2 py-0.5 rounded ${
                              q.priority === 'high'
                                ? 'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300'
                                : q.priority === 'medium'
                                ? 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300'
                                : 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300'
                            }`}
                          >
                            {q.priority} Priority
                          </span>
                          <span className="text-[10px] text-text-muted uppercase font-mono">
                            {q.state}
                          </span>
                        </div>
                        <p className="text-xs font-medium text-text-main line-clamp-2 leading-snug">
                          {q.text}
                        </p>
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          </Card>
        </div>

        {/* Right Column (7 cols): Selected Question & Answer Form */}
        <div className="lg:col-span-7">
          {currentQuestion ? (
            <Card className="p-4 sm:p-6 space-y-6">
              {/* Question Header & Priority */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span
                    className={`text-xs font-semibold uppercase px-2.5 py-1 rounded-md ${
                      currentQuestion.priority === 'high'
                        ? 'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300'
                        : 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300'
                    }`}
                  >
                    {currentQuestion.priority} Priority Gap
                  </span>
                  <span className="text-xs text-text-muted font-mono">ID: {currentQuestion.id}</span>
                </div>
                <h3 className="text-base font-bold text-text-main leading-snug">
                  {currentQuestion.text}
                </h3>
              </div>

              {/* Why We Ask + Evidentiary Quote */}
              <div className="p-4 bg-slate-50 dark:bg-slate-800/40 rounded-xl border border-border space-y-2">
                <div className="flex items-center gap-1.5 text-xs font-semibold text-text-main">
                  <Info className="w-4 h-4 text-navy dark:text-teal" />
                  <span>Why we ask this:</span>
                </div>
                <p className="text-xs text-text-muted leading-relaxed">
                  {currentQuestion.why_we_ask}
                </p>

                {currentQuestion.linked_quote && (
                  <div className="mt-2 pt-2 border-t border-border font-mono text-xs text-text-main bg-surface p-2.5 rounded-lg border border-border">
                    <span className="text-text-muted text-[10px] block uppercase font-sans mb-1">
                      From: {currentQuestion.linked_source || 'Project Records'}
                    </span>
                    &quot;{currentQuestion.linked_quote}&quot;
                  </div>
                )}
              </div>

              {/* Current Answer Display (if already answered) */}
              {currentQuestion.state === 'answered' && currentQuestion.answer && (
                <div className="p-4 bg-status-leaver-bg border border-status-leaver-border rounded-xl space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-status-leaver-text">
                      <UserCheck className="w-4 h-4" />
                      <span>Leaver-attested Answer</span>
                    </span>
                    <span className="text-[11px] text-purple-700 dark:text-purple-300 italic">
                      Recorded in ledger as attested (not verified)
                    </span>
                  </div>
                  <p className="text-sm text-text-main font-medium whitespace-pre-wrap">
                    {currentQuestion.answer}
                  </p>
                </div>
              )}

              {/* Answering Form (if Departing Member or Lead) */}
              {canAnswerInterview ? (
                <div className="space-y-3 pt-2 border-t border-border">
                  <div className="flex justify-between items-center text-xs font-semibold text-text-main">
                    <label>Provide Clarification or Context</label>
                    <span className="text-[11px] text-text-muted font-mono">
                      {answerInput.length} characters
                    </span>
                  </div>

                  <textarea
                    rows={4}
                    value={answerInput}
                    onChange={(e) => setAnswerInput(e.target.value)}
                    placeholder="Describe the background, decision reason, or handover instructions..."
                    className="w-full text-sm p-3 border border-border rounded-btn bg-surface text-text-main focus:ring-2 focus:ring-navy focus:outline-none"
                  />

                  <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
                    <div className="flex items-center gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => skipMutation.mutate(currentQuestion.id)}
                        isLoading={skipMutation.isPending}
                        leftIcon={<SkipForward className="w-3.5 h-3.5" />}
                      >
                        Skip for now
                      </Button>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => unknownMutation.mutate(currentQuestion.id)}
                        isLoading={unknownMutation.isPending}
                      >
                        I don&apos;t know / unrecorded
                      </Button>
                    </div>

                    <Button
                      variant="primary"
                      size="md"
                      disabled={!answerInput.trim() || answerMutation.isPending}
                      isLoading={answerMutation.isPending}
                      onClick={() =>
                        answerMutation.mutate({
                          id: currentQuestion.id,
                          answer: answerInput.trim(),
                        })
                      }
                      leftIcon={<Send className="w-4 h-4" />}
                    >
                      Save Answer to Ledger
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="p-4 bg-slate-50 dark:bg-slate-800/40 border border-border rounded-lg text-xs text-text-muted italic">
                  Answering exit interview questions is restricted to the Departing Member{isDemo && leaverName ? ` (${leaverName})` : ''} and Project Lead.
                </div>
              )}
            </Card>
          ) : (
            <Card className="p-12 text-center text-text-muted">
              <HelpCircle className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm font-medium text-text-main">Select a question to view details.</p>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};
