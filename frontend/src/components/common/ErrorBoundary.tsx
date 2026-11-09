import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from './Button';
import { sanitizeSecrets } from '../../utils/sanitize';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('HandoverLedger UI Uncaught Error:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-[50vh] flex flex-col items-center justify-center p-6 text-center">
          <div className="w-14 h-14 rounded-2xl bg-rose-100 dark:bg-rose-950/50 flex items-center justify-center text-rose-600 mb-4 shadow-sm">
            <AlertTriangle className="w-7 h-7" />
          </div>
          <h2 className="text-xl font-bold text-text-main">An unexpected interface error occurred</h2>
          <p className="text-xs text-text-muted mt-1.5 max-w-md font-mono bg-bg-surface px-2 py-1 rounded border border-border-subtle break-all">
            {sanitizeSecrets(this.state.error?.message) || 'Something went wrong rendering this component.'}
          </p>
          <div className="mt-5">
            <Button
              variant="primary"
              size="sm"
              onClick={() => {
                this.setState({ hasError: false });
                window.location.reload();
              }}
              leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
            >
              Reload Interface
            </Button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

