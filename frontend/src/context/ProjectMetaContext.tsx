import React, { createContext, useContext, ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import { ProjectData, ProjectMode } from '../types';

interface ProjectMetaContextType {
  data: ProjectData | undefined;
  isLoading: boolean;
  mode: ProjectMode;
  displayName: string | null;
  leaverName: string | null;
  isDemo: boolean;
  isOwn: boolean;
  isEmpty: boolean;
  refetch: () => void;
}

const ProjectMetaContext = createContext<ProjectMetaContextType | undefined>(undefined);

export const ProjectMetaProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['project'],
    queryFn: api.getProject,
    staleTime: 5000,
  });

  const mode: ProjectMode = data?.mode || (data?.name === 'Campus Connect' ? 'demo' : 'empty');
  const isDemo = mode === 'demo';
  const isOwn = mode === 'own';
  const isEmpty = mode === 'empty';

  const displayName = isDemo ? (data?.display_name || 'Campus Connect') : null;
  const leaverName = isDemo ? (data?.leaver_name || 'Arjun Mehta') : null;

  return (
    <ProjectMetaContext.Provider
      value={{
        data,
        isLoading,
        mode,
        displayName,
        leaverName,
        isDemo,
        isOwn,
        isEmpty,
        refetch,
      }}
    >
      {children}
    </ProjectMetaContext.Provider>
  );
};

export const useProjectMeta = (): ProjectMetaContextType => {
  const context = useContext(ProjectMetaContext);
  if (!context) {
    throw new Error('useProjectMeta must be used within a ProjectMetaProvider');
  }
  return context;
};
