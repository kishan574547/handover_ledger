import React, { useState, useEffect, useCallback } from 'react';
import { WifiOff, RefreshCw } from 'lucide-react';
import { api, API_BASE_URL } from '../../api/client';

export const OfflineBanner: React.FC = () => {
  const [isOffline, setIsOffline] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);

  const checkConnectivity = useCallback(async () => {
    try {
      await api.healthCheck();
      setIsOffline(false);
    } catch {
      setIsOffline(true);
    }
  }, []);

  useEffect(() => {
    checkConnectivity();
    const interval = setInterval(checkConnectivity, 15000);
    return () => clearInterval(interval);
  }, [checkConnectivity]);

  const handleRetry = async () => {
    setIsRetrying(true);
    try {
      await api.healthCheck();
      setIsOffline(false);
    } catch {
      setIsOffline(true);
    } finally {
      setIsRetrying(false);
    }
  };

  if (!isOffline) return null;

  return (
    <div
      data-testid="offline-banner"
      className="bg-rose-600 text-white px-4 py-2.5 text-xs font-medium flex items-center justify-between shadow-md relative z-50 animate-fadeIn"
    >
      <div className="flex items-center gap-2">
        <WifiOff className="w-4 h-4 text-rose-100 flex-shrink-0 animate-pulse" />
        <span>
          <strong>Backend Offline:</strong> Cannot reach the HandoverLedger API at{' '}
          <code className="bg-rose-700/60 px-1 py-0.5 rounded text-[11px] font-mono">{API_BASE_URL}</code>.
          Please verify the backend server is running.
        </span>
      </div>
      <button
        onClick={handleRetry}
        disabled={isRetrying}
        className="flex items-center gap-1.5 bg-white text-rose-700 px-3 py-1 rounded-md font-semibold text-xs hover:bg-rose-50 active:scale-95 transition-all flex-shrink-0 disabled:opacity-75"
      >
        <RefreshCw className={`w-3.5 h-3.5 ${isRetrying ? 'animate-spin' : ''}`} />
        <span>{isRetrying ? 'Connecting...' : 'Retry Connection'}</span>
      </button>
    </div>
  );
};

