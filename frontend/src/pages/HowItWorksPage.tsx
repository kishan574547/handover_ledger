import React from 'react';
import {
  Link2,
  FileSearch,
  CheckCircle2,
  ShieldCheck,
  Send,
  HelpCircle,
  AlertTriangle,
  Lock,
  Sparkles,
  Info,
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '../components/common/Card';
import { StatusBadge, ClearanceBadge } from '../components/common/Badge';

export const HowItWorksPage: React.FC = () => {
  return (
    <div className="space-y-8 max-w-4xl mx-auto pb-12">
      {/* Hero Header */}
      <div>
        <h2 className="text-2xl font-bold text-slate-900 tracking-tight">How HandoverLedger Works</h2>
        <p className="text-sm text-slate-500 mt-1">
          A verifiable, dual-check knowledge ledger that turns unstructured project records into trustworthy handover documentation.
        </p>
      </div>

      {/* 5-Step Core Workflow */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-bold text-slate-900">
            The 5-Step Handover Workflow
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            {[
              {
                step: '1',
                title: 'Connect',
                icon: <Link2 className="w-5 h-5 text-navy" />,
                desc: 'Ingest public GitHub repo, meeting notes (.md, .txt, .pdf), or chat logs (.txt, .json). Sensitive secrets, emails, and phone numbers are automatically masked before any AI processing.',
              },
              {
                step: '2',
                title: 'Reconstruct',
                icon: <FileSearch className="w-5 h-5 text-blue-600" />,
                desc: 'The pipeline decomposes unstructured history into atomic factual claims: architecture decisions, open work, owners, dependencies, and recurring problems.',
              },
              {
                step: '3',
                title: 'Verify',
                icon: <CheckCircle2 className="w-5 h-5 text-emerald-600" />,
                desc: 'Dual-check verification: rapidfuzz fuzzy matches the quote in the source chunk (threshold >= 90%), while an independent check evaluates support. Only both together yield "Verified".',
              },
              {
                step: '4',
                title: 'Review',
                icon: <ShieldCheck className="w-5 h-5 text-purple-600" />,
                desc: 'Project leads resolve conflicts, review missing gaps, conduct the exit interview with the leaver, freeze snapshot versions, and approve release.',
              },
              {
                step: '5',
                title: 'Handover',
                icon: <Send className="w-5 h-5 text-teal" />,
                desc: 'Each incoming member receives a role-tailored view containing ONLY claims they are cleared to see. Run leak check, export Markdown, or acknowledge receipt.',
              },
            ].map((st) => (
              <div key={st.step} className="p-4 bg-slate-50 rounded-xl border border-slate-200 flex flex-col items-start gap-2">
                <div className="w-8 h-8 rounded-lg bg-white border border-slate-200 flex items-center justify-center font-bold text-xs text-navy shadow-xs">
                  {st.step}
                </div>
                <div className="flex items-center gap-1.5 font-semibold text-slate-900 text-sm mt-1">
                  {st.icon}
                  <span>{st.title}</span>
                </div>
                <p className="text-xs text-slate-600 leading-relaxed">{st.desc}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Status Legend */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-bold text-slate-900">
            Trust Rules: Claim Status Legend
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-xs">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 bg-status-verified-bg/40 border border-status-verified-border rounded-xl space-y-1.5">
              <div className="flex items-center gap-2">
                <StatusBadge status="verified" />
                <span className="font-semibold text-status-verified-text">Verifiable Fact</span>
              </div>
              <p className="text-slate-700 leading-relaxed">
                Dual check passed: The quoted text was confirmed to exist verbatim inside the source chunk (fuzzy match score &gt;= 90%), AND independent check confirmed it substantiates the claim.
              </p>
            </div>

            <div className="p-4 bg-status-inferred-bg/40 border border-status-inferred-border rounded-xl space-y-1.5">
              <div className="flex items-center gap-2">
                <StatusBadge status="inferred" />
                <span className="font-semibold text-status-inferred-text">Contextual Deduction</span>
              </div>
              <p className="text-slate-700 leading-relaxed">
                The passage exists in the source, but only partially supports the statement, or requires circumstantial inference.
              </p>
            </div>

            <div className="p-4 bg-status-conflicting-bg/40 border border-status-conflicting-border rounded-xl space-y-1.5">
              <div className="flex items-center gap-2">
                <StatusBadge status="conflicting" />
                <span className="font-semibold text-status-conflicting-text">Direct Contradiction</span>
              </div>
              <p className="text-slate-700 leading-relaxed">
                Two different project sources state contradictory values (e.g. 30s timeout in meeting notes vs 10s in chat). Highlighted until reconciled by the lead.
              </p>
            </div>

            <div className="p-4 bg-status-missing-bg/40 border border-status-missing-border rounded-xl space-y-1.5">
              <div className="flex items-center gap-2">
                <StatusBadge status="missing" />
                <span className="font-semibold text-status-missing-text">Identified Gap</span>
              </div>
              <p className="text-slate-700 leading-relaxed">
                An essential rationale, owner, stalled task, or dependency was missing from the documentation. Triggers exit interview questions.
              </p>
            </div>
          </div>

          <div className="p-4 bg-status-leaver-bg border border-status-leaver-border rounded-xl space-y-1.5">
            <div className="flex items-center gap-2">
              <StatusBadge status="inferred" isLeaverAttested={true} />
              <span className="font-semibold text-status-leaver-text">Leaver-Attested (Never Verified)</span>
            </div>
            <p className="text-slate-700 leading-relaxed">
              Information provided by the leaving person during the exit interview. In accordance with the Trust Rules, leaver statements are recorded honestly as attested, but are never marked as Verified because no pre-existing commit or document corroborates them.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Clearance Model */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-bold text-slate-900">
            Clearance Levels & Role Hierarchy
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-xs leading-relaxed text-slate-700">
          <p>
            Clearance filtering is enforced strictly <strong>inside the database query layer</strong>, not in route code. A claim&apos;s clearance is calculated as the highest clearance level among its evidentiary sources.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2">
            <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg space-y-1">
              <ClearanceBadge clearance={1} />
              <p className="font-semibold text-emerald-950 mt-1">Level 1: General</p>
              <p className="text-slate-600">Accessible to all team members: Coordinator, Developer, Departing, and Lead.</p>
            </div>
            <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg space-y-1">
              <ClearanceBadge clearance={2} />
              <p className="font-semibold text-blue-950 mt-1">Level 2: Technical</p>
              <p className="text-slate-600">Deployment architecture, Docker configs, and code risks. Visible to Developer, Departing, and Lead.</p>
            </div>
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg space-y-1">
              <ClearanceBadge clearance={3} />
              <p className="font-semibold text-rose-950 mt-1">Level 3: Confidential</p>
              <p className="text-slate-600">Production DB disaster recovery credentials and escalation keys. Restricted strictly to Project Lead.</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Honest Limitations List */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-bold text-slate-900">
            Known System Limitations
          </CardTitle>
        </CardHeader>
        <CardContent className="text-xs space-y-2 text-slate-700 leading-relaxed">
          <ul className="list-disc pl-5 space-y-1.5">
            <li>
              <strong>Heuristic Fallback:</strong> If Gemini is unreachable or rate-limited, the system falls back to cached results or token-overlap heuristics rather than fabricating claims.
            </li>
            <li>
              <strong>Simulated Role Headers:</strong> In demo mode, roles are switched via client headers (<code className="bg-slate-100 px-1 py-0.5 rounded">X-Demo-Role</code>) rather than a production OAuth session.
            </li>
            <li>
              <strong>Binary Verification:</strong> Fuzzy match scoring uses a strict 90% threshold. Passages with typos or severe rephrasing will be marked Inferred rather than Verified.
            </li>
            <li>
              <strong>Scope Boundaries:</strong> In v1, conflict timelines are kept simple; full conflict overlays and per-item acknowledgements are reserved for subsequent releases.
            </li>
          </ul>
        </CardContent>
      </Card>

      {/* Footnote */}
      <div className="text-center text-xs text-slate-400 py-4 border-t border-slate-200">
        Built with AI assistance (Antigravity, Gemini). Designed for transparent, verifiable team handovers.
      </div>
    </div>
  );
};

