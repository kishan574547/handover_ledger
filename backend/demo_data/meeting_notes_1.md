# Campus Connect - Core Team Sync 1
**Date**: 2026-08-10  
**Attendees**: Arjun Mehta (Tech Lead), Priya Nair (Club President), Sneha Iyer (Coordinator)  
**Clearance**: General  

## Agenda & Discussion
1. **Architecture Blueprint**:
   - Agreed to build Campus Connect using FastAPI for backend and React Vite on frontend.
   - Core database schema will use PostgreSQL hosted on Supabase in cloud.
2. **Backend Configuration**:
   - Production API timeout is configured to 30s in backend settings to allow batch roster uploads from campus admins.
3. **Module Ownership**:
   - Payments integration and ticketing module is officially assigned to Arjun Mehta as lead owner.
   - Sneha Iyer will handle club event registration workflows and coordination.
4. **Design Decisions**:
   - Dropped dark mode support for v1 release.
   - Initial authentication will use college SSO email domain validation (@campus.edu).

