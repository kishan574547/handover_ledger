import React, { useState, useEffect } from 'react';
import { ShieldCheck } from 'lucide-react';

interface SplashScreenProps {
  children: React.ReactNode;
}

export const SplashScreen: React.FC<SplashScreenProps> = ({ children }) => {
  const [showSplash, setShowSplash] = useState<boolean>(() => {
    // Check if ?nosplash=1 is in URL (for automation/tests)
    try {
      const searchParams = new URLSearchParams(window.location.search);
      if (searchParams.get('nosplash') === '1') {
        return false;
      }
      // Ensure any legacy session flag is cleared so refresh always opens freshly
      sessionStorage.removeItem('handover_seen_splash');
    } catch {
      // In case URL or sessionStorage is restricted
    }
    // Always start with splash screen freshly on every page load / refresh
    return true;
  });

  const [progress, setProgress] = useState(0);
  const [isFadingOut, setIsFadingOut] = useState(false);

  useEffect(() => {
    if (!showSplash) return;

    const startTime = Date.now();
    const duration = 2000; // 2.0s duration

    const interval = setInterval(() => {
      const elapsed = Date.now() - startTime;
      const pct = Math.min(100, Math.floor((elapsed / duration) * 100));
      setProgress(pct);

      if (elapsed >= duration) {
        clearInterval(interval);
        setIsFadingOut(true);
        setTimeout(() => {
          setShowSplash(false);
        }, 300);
      }
    }, 25);

    return () => clearInterval(interval);
  }, [showSplash]);

  if (!showSplash) {
    return <>{children}</>;
  }

  // Dynamic status text corresponding to initialization stage
  let statusText = 'INITIALIZING LEDGER...';
  if (progress >= 30 && progress < 65) {
    statusText = 'VERIFYING CRYPTOGRAPHIC CLAIMS...';
  } else if (progress >= 65 && progress < 90) {
    statusText = 'PREPARING WORKSPACE...';
  } else if (progress >= 90) {
    statusText = 'WORKSPACE READY';
  }

  return (
    <div
      data-testid="splash-screen"
      className={`fixed inset-0 z-[9999] flex flex-col items-center justify-center bg-slate-950 text-white select-none transition-opacity duration-300 ${
        isFadingOut ? 'opacity-0 pointer-events-none' : 'opacity-100'
      }`}
    >
      {/* Background radial glow */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(15,118,110,0.15)_0%,transparent_70%)] pointer-events-none" />

      <div className="relative z-10 flex flex-col items-center max-w-xl px-6 sm:px-8 text-center animate-fadeIn">
        {/* Large Prominent Shield Icon with glowing layers */}
        <div className="relative mb-6 sm:mb-8 flex items-center justify-center">
          <div className="w-20 h-20 sm:w-24 sm:h-24 md:w-28 md:h-28 rounded-3xl bg-gradient-to-tr from-teal-500 via-teal-400 to-indigo-600 flex items-center justify-center shadow-2xl shadow-teal-500/30 ring-1 ring-white/20">
            <ShieldCheck className="w-11 h-11 sm:w-13 sm:h-13 md:w-16 md:h-16 text-white drop-shadow-md" />
          </div>
          {/* Ambient outer glow */}
          <div className="absolute -inset-2 rounded-3xl bg-teal-400/25 blur-xl -z-10 animate-pulse" />
          <div className="absolute -inset-4 rounded-3xl bg-indigo-500/20 blur-2xl -z-20" />
        </div>

        {/* Brand Title: Substantially larger and bold */}
        <h1 className="text-3xl sm:text-4xl md:text-5xl font-black tracking-tight text-white font-mono">
          Handover<span className="text-teal-400 bg-gradient-to-r from-teal-400 to-emerald-400 bg-clip-text text-transparent">Ledger</span>
        </h1>

        {/* Subtitle */}
        <p className="text-sm sm:text-base md:text-lg text-slate-300 mt-3 font-medium tracking-wide max-w-md">
          Verifiable Project Handover & Knowledge Ledger
        </p>

        {/* Substantially Enlarged 0-100% Loader Bar */}
        <div className="w-72 sm:w-96 md:w-[420px] mt-8 sm:mt-10">
          <div className="h-2.5 sm:h-3 w-full bg-slate-900 border border-slate-700/60 rounded-full p-0.5 overflow-hidden shadow-inner">
            <div
              className="h-full bg-gradient-to-r from-teal-400 via-emerald-400 to-indigo-500 rounded-full transition-all duration-75 ease-out shadow-[0_0_14px_rgba(45,212,191,0.6)]"
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="flex justify-between items-center text-xs sm:text-sm text-slate-400 font-mono mt-3">
            <span className="tracking-wider uppercase">{statusText}</span>
            <span className="font-bold text-teal-400 text-sm sm:text-base tabular-nums">
              {progress}%
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
