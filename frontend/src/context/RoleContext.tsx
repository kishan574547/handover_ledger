import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { DemoRole } from '../types';
import { getStoredRole, setStoredRole } from '../api/client';
import { useToast } from './ToastContext';

export interface RoleConfig {
  id: DemoRole;
  label: string;
  name: string;
  clearance: number;
  clearanceLabel: string;
  description: string;
}

export const ROLE_DETAILS: Record<DemoRole, RoleConfig> = {
  departing: {
    id: 'departing',
    label: 'Departing Member',
    name: 'Arjun Mehta',
    clearance: 2,
    clearanceLabel: 'Level 2: Technical',
    description: 'Tech Lead graduating; answers exit interview questions, reviews ledger.',
  },
  lead: {
    id: 'lead',
    label: 'Project Lead',
    name: 'Priya Nair',
    clearance: 3,
    clearanceLabel: 'Level 3: Confidential',
    description: 'Club President with full clearance; reviews, approves, and releases handover.',
  },
  developer: {
    id: 'developer',
    label: 'Successor Developer',
    name: 'Rahul Verma',
    clearance: 2,
    clearanceLabel: 'Level 2: Technical',
    description: 'Incoming developer; reads technical handover, runs leak check, acknowledges receipt.',
  },
  coordinator: {
    id: 'coordinator',
    label: 'Coordinator',
    name: 'Sneha Iyer',
    clearance: 1,
    clearanceLabel: 'Level 1: General',
    description: 'Club events coordinator; views general operational handover only.',
  },
};

interface RoleContextType {
  role: DemoRole;
  roleConfig: RoleConfig;
  setRole: (role: DemoRole) => void;
  canLead: boolean;
  canAnswerInterview: boolean;
  canAcknowledge: boolean;
}

const RoleContext = createContext<RoleContextType | undefined>(undefined);

export const RoleProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [role, setRoleState] = useState<DemoRole>(getStoredRole());
  const queryClient = useQueryClient();
  const { info } = useToast();

  const handleSetRole = (newRole: DemoRole) => {
    setRoleState(newRole);
    setStoredRole(newRole);
    // Invalidate queries so all views refetch according to new clearance & permissions
    queryClient.invalidateQueries();
    const config = ROLE_DETAILS[newRole];
    info(`Switched Role: ${config.label}`, `Viewing as ${config.name} (${config.clearanceLabel})`);
  };

  const roleConfig = ROLE_DETAILS[role] || ROLE_DETAILS.lead;
  const canLead = role === 'lead';
  const canAnswerInterview = role === 'departing' || role === 'lead';
  const canAcknowledge = role === 'developer' || role === 'coordinator' || role === 'lead';

  return (
    <RoleContext.Provider
      value={{
        role,
        roleConfig,
        setRole: handleSetRole,
        canLead,
        canAnswerInterview,
        canAcknowledge,
      }}
    >
      {children}
    </RoleContext.Provider>
  );
};

export const useRole = () => {
  const context = useContext(RoleContext);
  if (!context) {
    throw new Error('useRole must be used within a RoleProvider');
  }
  return context;
};
