import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
import { BottomNav } from './BottomNav';

export const Layout: React.FC = () => {
  const [isMobileDrawerOpen, setIsMobileDrawerOpen] = useState(false);

  return (
    <div className="flex min-h-[100dvh] w-full max-w-full overflow-x-hidden bg-background text-text-main">
      {/* Sidebar (Desktop persistent + Mobile off-canvas drawer) */}
      <Sidebar
        isMobileDrawerOpen={isMobileDrawerOpen}
        onCloseMobileDrawer={() => setIsMobileDrawerOpen(false)}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 w-full overflow-x-hidden min-h-[100dvh]">
        <Topbar onToggleMobileDrawer={() => setIsMobileDrawerOpen(true)} />

        {/* Main scrollable viewport with fluid padding and 1440px max-width */}
        <main className="flex-1 overflow-y-auto px-[clamp(16px,3vw,32px)] py-4 sm:py-6 pb-24 md:pb-8 focus:outline-none">
          <div className="max-w-[1440px] mx-auto w-full">
            <Outlet />
          </div>
        </main>

        {/* Bottom Navigation for mobile phones (< 768px) */}
        <BottomNav onOpenMore={() => setIsMobileDrawerOpen(true)} />
      </div>
    </div>
  );
};
