import React from 'react';
import { NavLink } from 'react-router-dom';
import { Menu } from 'lucide-react';
import { useRole } from '../../context/RoleContext';
import { getPhoneBottomNavItems } from '../../config/navigation';

interface BottomNavProps {
  onOpenMore: () => void;
}

export const BottomNav: React.FC<BottomNavProps> = ({ onOpenMore }) => {
  const { role } = useRole();
  const navItems = getPhoneBottomNavItems(role);

  return (
    <nav
      className="fixed bottom-0 inset-x-0 z-40 bg-surface border-t border-border shadow-lg md:hidden flex items-center justify-around h-16 px-1 pb-[env(safe-area-inset-bottom)] bottom-nav select-none"
      aria-label="Mobile navigation"
    >
      {navItems.map((item) => {
        const Icon = item.icon;
        return (
          <NavLink
            key={item.id}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              `flex flex-col items-center justify-center flex-1 h-full min-h-[44px] min-w-[44px] py-1 text-[10px] font-medium transition-colors ${
                isActive
                  ? 'text-navy dark:text-teal font-semibold'
                  : 'text-text-muted hover:text-text-main'
              }`
            }
          >
            <Icon className="w-5 h-5 mb-0.5" />
            <span className="truncate max-w-[64px]">{item.shortLabel || item.label}</span>
          </NavLink>
        );
      })}

      {/* "More" trigger to open full drawer */}
      <button
        onClick={onOpenMore}
        className="flex flex-col items-center justify-center flex-1 h-full min-h-[44px] min-w-[44px] py-1 text-[10px] font-medium text-text-muted hover:text-text-main transition-colors"
        aria-label="Open full menu"
      >
        <Menu className="w-5 h-5 mb-0.5" />
        <span>More</span>
      </button>
    </nav>
  );
};
