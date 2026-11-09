import React, { useState } from 'react';
import { AlertCircle, RefreshCw, Copy, Check, ChevronDown, WifiOff, Clock } from 'lucide-react';
import { Button } from './Button';
import { sanitizeSecrets } from '../../utils/sanitize';

export interface ApiErrorDisplayProps {
  error: Error | any;
  onRetry?: () => void;
  className?: string;
  compact?: boolean;
}

export const ApiErrorDisplay: React.FC<ApiErrorDisplayProps> = ({
  error,
  onRetry,
  className = '',
  compact = false,
}) => {
  const [copied, setCopied] = useState(false);

  if (!error) return null;

  const message = error?.message || 'An unexpected error occurred.';
  const details = error?.details || (typeof error === 'string' ? error : error?.stack) || '';
  const sanitizedDetails = sanitizeSecrets(details).slice(0, 300);
  const kind = error?.kind || 'unknown';
  const statusCode = error?.statusCode;
  const url = error?.url;

  const handleCopyDiagnostics = () => {
    const diagnostics = {
      timestamp: new Date().toISOString(),
      kind,
      statusCode,
      url,
      message: sanitizeSecrets(message),
      details: sanitizedDetails,
      userAgent: navigator.userAgent,
    };
    navigator.clipboard.writeText(JSON.stringify(diagnostics, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  const getIcon = () => {
    if (kind === 'network') return <WifiOff className="w-4 h-4 text-rose-600 dark:text-rose-400 mt-0.5 flex-shrink-0" />;
    if (kind === 'timeout') return <Clock className="w-4 h-4 text-amber-600 dark:text-amber-400 mt-0.5 flex-shrink-0" />;
    return <AlertCircle className="w-4 h-4 text-rose-600 dark:text-rose-400 mt-0.5 flex-shrink-0" />;
  };

  return (
    <div
      className={`p-3.5 bg-rose-50/90 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900/80 rounded-card text-xs text-rose-900 dark:text-rose-200 space-y-2.5 transition-all ${className}`}
    >
      <div className="flex items-start gap-2.5">
        {getIcon()}
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-rose-950 dark:text-rose-100 break-words leading-relaxed">
            {message}
          </p>
          {statusCode && (
            <span className="inline-block mt-0.5 text-[10px] uppercase font-mono px-1.5 py-0.2 rounded bg-rose-200/60 dark:bg-rose-900/60 text-rose-800 dark:text-rose-300">
              HTTP {statusCode}
            </span>
          )}
        </div>
      </div>

      {sanitizedDetails && (
        <details className="group border-t border-rose-200/60 dark:border-rose-900/60 pt-2 text-[11px]">
          <summary className="cursor-pointer text-rose-700 dark:text-rose-300 font-medium hover:underline flex items-center gap-1 select-none">
            <ChevronDown className="w-3.5 h-3.5 transition-transform group-open:rotate-180" />
            <span>Show details</span>
          </summary>
          <div className="mt-1.5 p-2 bg-rose-100/50 dark:bg-rose-950/80 rounded font-mono text-[10px] break-all max-h-28 overflow-y-auto text-rose-900 dark:text-rose-200 border border-rose-200/50 dark:border-rose-900/50">
            {sanitizedDetails}
          </div>
        </details>
      )}

      <div className="flex items-center gap-2 pt-1 border-t border-rose-200/40 dark:border-rose-900/40">
        {onRetry && (
          <Button
            variant="outline"
            size="sm"
            onClick={onRetry}
            leftIcon={<RefreshCw className="w-3 h-3" />}
            className="text-[11px] h-7 px-2.5 bg-white dark:bg-bg-surface hover:bg-rose-100 dark:hover:bg-rose-950/60"
          >
            Retry
          </Button>
        )}
        <Button
          variant="outline"
          size="sm"
          onClick={handleCopyDiagnostics}
          leftIcon={copied ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
          className="text-[11px] h-7 px-2.5 bg-white dark:bg-bg-surface hover:bg-rose-100 dark:hover:bg-rose-950/60"
        >
          {copied ? 'Copied' : 'Copy diagnostics'}
        </Button>
      </div>
    </div>
  );
};
