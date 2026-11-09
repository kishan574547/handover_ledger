import React from 'react';
import { useNavigate } from 'react-router-dom';
import { FileQuestion, ArrowLeft, Home } from 'lucide-react';
import { Button } from '../components/common/Button';

export const NotFoundPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center text-center px-4 py-12">
      <div className="w-16 h-16 rounded-2xl bg-navy/10 dark:bg-teal/20 flex items-center justify-center text-navy dark:text-teal mb-4 shadow-sm">
        <FileQuestion className="w-8 h-8" />
      </div>
      <h2 className="text-3xl font-bold text-text-main tracking-tight">404 - Page Not Found</h2>
      <p className="text-sm text-text-muted mt-2 max-w-md leading-relaxed">
        The ledger view, source file, or route you requested does not exist or has been moved.
      </p>
      <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
        <Button variant="outline" onClick={() => navigate(-1)} leftIcon={<ArrowLeft className="w-4 h-4" />}>
          Go Back
        </Button>
        <Button variant="primary" onClick={() => navigate('/')} leftIcon={<Home className="w-4 h-4" />}>
          Return to Dashboard
        </Button>
      </div>
    </div>
  );
};

