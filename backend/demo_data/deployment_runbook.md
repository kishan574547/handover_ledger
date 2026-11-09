# Campus Connect - Deployment & Operations Runbook
**Classification**: Technical (Clearance Level 2)  
**Last Updated**: 2026-09-22 by Arjun Mehta  

## 1. Architecture Overview
- Web Frontend: React 18 SPA served via Nginx static container.
- Backend API: Python FastAPI with Uvicorn ASGI server.
- Database: PostgreSQL on Supabase (managed) with local SQLite fallback.

## 2. Server Deployment
- Production server setup runs inside Docker Compose.
- Systemd service `campusconnect-api.service` restarts automatically on server reboot.
- Port bindings: 8000 for backend API, 5173 / 80 for frontend web client.

## 3. Recurring Issues & Mitigations
- Background task memory bloat during CSV roster uploads:
  - Worker process is restricted to 512MB RAM with automatic recycling.
- SSL renew cron:
  - Executes every Monday at 03:00 UTC via Certbot.

## 4. Dependencies
- Supabase PostgreSQL v15
- Redis v7 for session cache
- Docker 24.0+

