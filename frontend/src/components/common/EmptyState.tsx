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
    <div className="bg-white rounded-card border border-slate-200 border-dashed p-12 text-center flex flex-col items-center justify-center max-w-xl mx-auto my-8 shadow-soft">
      <div className="w-16 h-16 rounded-2xl bg-slate-50 border border-slate-200 flex items-center justify-center text-slate-500 mb-4 shadow-sm">
        {icon}
      </div>
      <h3 className="text-lg font-semibold text-slate-900 mb-1">{title}</h3>
      <p className="text-sm text-slate-500 max-w-md mb-6">{description}</p>
      <div className="flex items-center gap-3">
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

