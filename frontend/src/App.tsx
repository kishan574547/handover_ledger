import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from './context/ThemeContext';
import { ToastProvider } from './context/ToastContext';
import { RoleProvider } from './context/RoleContext';
import { Layout } from './components/layout/Layout';

import { DashboardPage } from './pages/DashboardPage';
import { SourcesPage } from './pages/SourcesPage';
import { ClaimLedgerPage } from './pages/ClaimLedgerPage';
import { TimelinePage } from './pages/TimelinePage';
import { ExitInterviewPage } from './pages/ExitInterviewPage';
import { ReviewApprovePage } from './pages/ReviewApprovePage';
import { HandoverPage } from './pages/HandoverPage';
import { ActivityPage } from './pages/ActivityPage';
import { HowItWorksPage } from './pages/HowItWorksPage';
import { SettingsPage } from './pages/SettingsPage';
import { AskHandoverPage } from './pages/AskHandoverPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 10000,
    },
  },
});

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <ToastProvider>
          <BrowserRouter>
            <RoleProvider>
              <Routes>
                <Route path="/" element={<Layout />}>
                  <Route index element={<DashboardPage />} />
                  <Route path="sources" element={<SourcesPage />} />
                  <Route path="ledger" element={<ClaimLedgerPage />} />
                  <Route path="timeline" element={<TimelinePage />} />
                  <Route path="interview" element={<ExitInterviewPage />} />
                  <Route path="review" element={<ReviewApprovePage />} />
                  <Route path="handover" element={<HandoverPage />} />
                  <Route path="ask" element={<AskHandoverPage />} />
                  <Route path="activity" element={<ActivityPage />} />
                  <Route path="how-it-works" element={<HowItWorksPage />} />
                  <Route path="settings" element={<SettingsPage />} />
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Route>
              </Routes>
            </RoleProvider>
          </BrowserRouter>
        </ToastProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
};
