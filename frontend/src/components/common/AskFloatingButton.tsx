import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { MessageSquareQuote } from 'lucide-react';

export const AskFloatingButton: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  // Don't render floating button if already on Ask the Handover page
  if (location.pathname === '/ask') {
    return null;
  }

  return (
    <button
      onClick={() => navigate('/ask')}
      className="fixed z-floating w-14 h-14 rounded-full bg-navy text-white hover:bg-navy-hover dark:bg-teal dark:text-slate-950 shadow-card flex items-center justify-center transition-all duration-200 hover:scale-105 active:scale-95 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-navy dark:focus-visible:ring-teal select-none group"
      style={{
        bottom: 'calc(var(--bottom-nav-h, 0px) + var(--action-bar-h, 0px) + 16px + env(safe-area-inset-bottom, 0px))',
        right: 'clamp(16px, 2.5vw, 24px)',
      }}
      title="Ask the Handover (Grounded Q&A)"
      aria-label="Ask the Handover (Grounded Q&A)"
    >
      <MessageSquareQuote className="w-6 h-6 transition-transform group-hover:scale-110" />
      {/* Visual pulse indicator */}
      <span className="absolute top-1 right-1 w-3 h-3 rounded-full bg-teal dark:bg-navy border-2 border-surface flex items-center justify-center">
        <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
      </span>
    </button>
  );
};

