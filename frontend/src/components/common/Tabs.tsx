import React from 'react';

export interface TabItem {
  id: string;
  label: string;
  count?: number;
  icon?: React.ReactNode;
}

interface TabsProps {
  tabs: TabItem[];
  activeTab: string;
  onChange: (tabId: string) => void;
  className?: string;
}

export const Tabs: React.FC<TabsProps> = ({ tabs, activeTab, onChange, className = '' }) => {
  return (
    <div className={`flex items-center gap-1 border-b border-border overflow-x-auto no-scrollbar ${className}`}>
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            className={`flex items-center gap-2 px-3.5 sm:px-4 py-2.5 text-sm font-medium border-b-2 transition-all relative -mb-px whitespace-nowrap min-h-[44px] ${
              isActive
                ? 'border-navy dark:border-teal text-navy dark:text-teal font-semibold'
                : 'border-transparent text-text-muted hover:text-text-main hover:border-slate-300 dark:hover:border-slate-700'
            }`}
          >
            {tab.icon && <span className="w-4 h-4 flex-shrink-0">{tab.icon}</span>}
            <span>{tab.label}</span>
            {tab.count !== undefined && (
              <span
                className={`ml-1 text-xs px-2 py-0.5 rounded-full ${
                  isActive
                    ? 'bg-navy/10 dark:bg-teal/20 text-navy dark:text-teal font-semibold'
                    : 'bg-slate-100 dark:bg-slate-800 text-text-muted'
                }`}
              >
                {tab.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
};
