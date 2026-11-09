# Campus Connect - Mid-Sprint Architecture Review
**Date**: 2026-08-25  
**Attendees**: Arjun Mehta (Tech Lead), Priya Nair (Club President), Rahul Verma (Successor Developer)  
**Clearance**: General  

## Key Updates & Decisions
1. **Onboarding Rahul Verma**:
   - Rahul Verma joined as junior developer and will shadow Arjun during graduation handover.
2. **Database Migrations**:
   - Alembic migration scripts are set up in `/migrations`.
   - All migrations must run before backend startup via entrypoint script.
3. **Recurring Problems**:
   - Recurring socket timeout when polling campus LDAP server during peak registration hours (10 AM to 12 PM).
   - Temporary mitigation: cached LDAP tokens for 15 minutes in memory.
4. **Third Party Integrations**:
   - Razorpay payment gateway sandbox credentials verified.
   - External faculty mentor: Dr. Rao will review club compliance requirements before launch.

