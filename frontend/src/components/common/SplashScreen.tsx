import React, { useState, useEffect } from 'react';
import { ShieldCheck } from 'lucide-react';

interface SplashScreenProps {
  children: React.ReactNode;
}

export const SplashScreen: React.FC<SplashScreenProps> = ({ children }) => {
  const [showSplash, setShowSplash] = useState<boolean>(() => {
    // Check if ?nosplash=1 is in URL
    const searchParams = new URLSearchParams(window.location.search);
    if (searchParams.get('nosplash') === '1') {
      return false;
    }
    // Check if already seen in this session
    try {
      if (sessionStorage.getItem('handover_seen_splash') === 'true') {
        return false;
      }
    } catch {
      // In case sessionStorage is blocked
    }
    return true;
  });

  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (!showSplash) return;

    const startTime = Date.now();
    const duration = 2200; // 2.2s splash duration

    const interval = setInterval(() => {
      const elapsed = Date.now() - startTime;
      const pct = Math.min(100, Math.floor((elapsed / duration) * 100));
      setProgress(pct);

      if (elapsed >= duration) {
        clearInterval(interval);
        try {
          sessionStorage.setItem('handover_seen_splash', 'true');
        } catch {}
        setShowSplash(false);
      }
    }, 30);

    return () => clearInterval(interval);
  }, [showSplash]);

  if (!showSplash) {
    return <>{children}</>;
  }

  return (
    <div
      data-testid="splash-screen"
      className="fixed inset-0 z-[9999] flex flex-col items-center justify-center bg-slate-950 text-white select-none transition-opacity duration-300"
    >
      <div className="flex flex-col items-center max-w-sm px-6 text-center animate-fadeIn">
        <div className="relative mb-5 flex items-center justify-center">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-teal-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-teal-500/20">
            <ShieldCheck className="w-9 h-9 text-white" />
          </div>
          <div className="absolute -inset-1 rounded-2xl bg-teal-500/20 blur-sm -z-10 animate-pulse" />
        </div>

        <h1 className="text-2xl font-bold tracking-tight text-white font-mono">
          Handover<span className="text-teal-400">Ledger</span>
        </h1>
        <p className="text-xs text-slate-400 mt-1.5 font-medium tracking-wide">
          Verifiable Project Handover & Knowledge Ledger
        </p>

        {/* 0-100% Loader Bar */}
        <div className="w-56 mt-8">
          <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-teal-400 to-indigo-500 rounded-full transition-all duration-75 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="flex justify-between items-center text-[10px] text-slate-500 font-mono mt-2">
            <span>INITIALIZING LEDGER</span>
            <span className="font-semibold text-teal-400">{progress}%</span>
          </div>
        </div>
      </div>
    </div>
  );
};
