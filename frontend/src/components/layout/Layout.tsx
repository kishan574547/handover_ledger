import React, { useState, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
import { BottomNav } from './BottomNav';
import { CommandPalette } from '../common/CommandPalette';
import { JudgeGuide } from '../common/JudgeGuide';

export const Layout: React.FC = () => {
  const [isMobileDrawerOpen, setIsMobileDrawerOpen] = useState(false);
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);

  // Global Ctrl+K / Cmd+K handler
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setIsCommandPaletteOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <div className="flex min-h-[100dvh] w-full max-w-full overflow-x-hidden bg-background text-text-main">
      {/* Sidebar (Desktop persistent + Mobile off-canvas drawer) */}
      <Sidebar
        isMobileDrawerOpen={isMobileDrawerOpen}
        onCloseMobileDrawer={() => setIsMobileDrawerOpen(false)}
      />

      {/* Main Content Viewport */}
      <div className="flex-1 flex flex-col min-w-0 w-full overflow-x-hidden min-h-[100dvh]">
        <Topbar
          onToggleMobileDrawer={() => setIsMobileDrawerOpen(true)}
          onOpenCommandPalette={() => setIsCommandPaletteOpen(true)}
        />

        {/* Content area: max-width 1440px centred, fluid padding */}
        <main className="flex-1 overflow-y-auto px-[clamp(16px,3vw,32px)] py-4 sm:py-6 pb-24 md:pb-8 focus:outline-none">
          <div className="max-w-[1440px] mx-auto w-full">
            <Outlet />
          </div>
        </main>

        {/* Mobile bottom nav on phones (< 768px) */}
        <BottomNav onOpenMore={() => setIsMobileDrawerOpen(true)} />

        {/* Global Signature Components */}
        <CommandPalette
          isOpen={isCommandPaletteOpen}
          onClose={() => setIsCommandPaletteOpen(false)}
        />
        <JudgeGuide />
      </div>
    </div>
  );
};
