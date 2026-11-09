import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { DemoRole } from '../types';
import { getStoredRole, setStoredRole } from '../api/client';
import { useToast } from './ToastContext';
import { ALL_NAV_ITEMS } from '../config/navigation';

export interface RoleConfig {
  id: DemoRole;
  label: string;
  name: string;
  clearance: number;
  clearanceLabel: string;
  description: string;
}

export interface RoleConfig {
  id: DemoRole;
  label: string;
  name: string;
  demoName: string;
  clearance: number;
  clearanceLabel: string;
  description: string;
}

export const ROLE_DETAILS: Record<DemoRole, RoleConfig> = {
  departing: {
    id: 'departing',
    label: 'Departing Member',
    name: 'Departing Member',
    demoName: 'Arjun Mehta',
    clearance: 2,
    clearanceLabel: 'Level 2: Technical',
    description: 'Outbound member; answers exit interview questions, reviews ledger.',
  },
  lead: {
    id: 'lead',
    label: 'Project Lead',
    name: 'Project Lead',
    demoName: 'Priya Nair',
    clearance: 3,
    clearanceLabel: 'Level 3: Confidential',
    description: 'Lead reviewer with full clearance; reviews, approves, and releases handover.',
  },
  developer: {
    id: 'developer',
    label: 'Successor Developer',
    name: 'Successor Developer',
    demoName: 'Rahul Verma',
    clearance: 2,
    clearanceLabel: 'Level 2: Technical',
    description: 'Incoming developer; reads technical handover, runs leak check, acknowledges receipt.',
  },
  coordinator: {
    id: 'coordinator',
    label: 'Coordinator',
    name: 'Coordinator',
    demoName: 'Sneha Iyer',
    clearance: 1,
    clearanceLabel: 'Level 1: General',
    description: 'Team coordinator; views general operational handover only.',
  },
};

interface RoleContextType {
  role: DemoRole;
  roleConfig: RoleConfig;
  setRole: (role: DemoRole) => void;
  canLead: boolean;
  canAnswerInterview: boolean;
  canAcknowledge: boolean;
  isRouteAllowed: (pathname: string, checkRole?: DemoRole) => boolean;
}

const RoleContext = createContext<RoleContextType | undefined>(undefined);

export const RoleProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  // First visit defaults to 'lead' role so judges see full workflow
  const [role, setRoleState] = useState<DemoRole>(() => {
    const stored = getStoredRole();
    return stored || 'lead';
  });

  const queryClient = useQueryClient();
  const { info } = useToast();
  const location = useLocation();
  const navigate = useNavigate();

  const isRouteAllowed = (pathname: string, targetRole: DemoRole = role): boolean => {
    // Normalise pathname
    const cleanPath = pathname.split('?')[0].split('#')[0];
    if (cleanPath === '/' || cleanPath === '') return true;

    const matchedNav = ALL_NAV_ITEMS.find((item) => {
      if (item.to === '/') return cleanPath === '/';
      return cleanPath.startsWith(item.to);
    });

    if (!matchedNav) return true; // Unmatched or 404
    return matchedNav.allowedRoles.includes(targetRole);
  };

  const handleSetRole = (newRole: DemoRole) => {
    setRoleState(newRole);
    setStoredRole(newRole);

    // Invalidate queries so all views refetch according to new clearance & permissions
    queryClient.invalidateQueries();
    const config = ROLE_DETAILS[newRole];
    info(`Switched Role: ${config.label}`, `Viewing as ${config.name} (${config.clearanceLabel})`);

    // Redirect to Dashboard if current page is not allowed for the new role
    if (!isRouteAllowed(location.pathname, newRole)) {
      navigate('/', { replace: true });
    }
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
        isRouteAllowed,
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
