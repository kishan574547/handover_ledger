import React from 'react';
import { Button } from './Button';

interface EmptyStateProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  actionText?: string;
  onAction?: () => void;
  actionVariant?: 'primary' | 'secondary' | 'accent';
  actionIcon?: React.ReactNode;
  secondaryAction?: React.ReactNode;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  actionText,
  onAction,
  actionVariant = 'primary',
  actionIcon,
  secondaryAction,
}) => {
  return (
    <div className="bg-surface rounded-card border border-border border-dashed p-8 sm:p-12 text-center flex flex-col items-center justify-center max-w-xl mx-auto my-6 sm:my-8 shadow-soft">
      <div className="w-14 h-14 sm:w-16 sm:h-16 rounded-2xl bg-slate-50 dark:bg-slate-800/80 border border-border flex items-center justify-center text-text-muted mb-4 shadow-sm">
        {icon}
      </div>
      <h3 className="text-base sm:text-lg font-semibold text-text-main mb-1">{title}</h3>
      <p className="text-sm text-text-muted max-w-md mb-6">{description}</p>
      <div className="flex flex-wrap items-center justify-center gap-3">
        {actionText && onAction && (
          <Button variant={actionVariant} onClick={onAction} leftIcon={actionIcon}>
            {actionText}
          </Button>
        )}
        {secondaryAction}
      </div>
    </div>
  );
};
