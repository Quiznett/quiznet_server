# QuizNet — Backend Overview

## Author - Ashvin Kausar, Kartikeya Singh Parihar

## Introduction

This document provides a concise, repo-ready introduction to the **QuizNet** backend (Django + DRF). It explains the purpose, implemented features, high-level architecture, important views/endpoints, middleware, and suggestions for future improvements. Add this `README`-style Markdown file to the server repository as `backend_INTRO.md` or similar.

---

## Purpose

The backend implements the application logic, data storage and real-time features for QuizNet. It exposes RESTful APIs used by the frontend, manages authentication and sessions, handles OTP email verification, executes real-time events (live quizzes, chat) via WebSockets, and persists quiz, user and result data in PostgreSQL.

---

## Key Features Provided by the Backend

- **User authentication & session management**
  - JWT access + refresh token generation
  - HttpOnly cookie-based token storage (access_token, refresh_token)
  - OTP-based email verification
  - Login, register, logout endpoints

- **Quiz management**
  - Create, read, update, delete (CRUD) quizzes
  - Add / edit / remove questions
  - Publish/unpublish quizzes and set metadata (difficulty, tags)
  - Quiz attempt recording and scoring

- **Real-time capabilities**
  - Live quiz hosting and participation via Django Channels + Redis
  - Real-time leaderboards and participant presence
  - Group chat and notifications

- **Middleware utilities**
  - Automatic access-token refresh from refresh cookie
  - Cookie helpers to set secure attributes depending on environment
  - CORS support for Netlify <-> Render deployments

- **Admin and analytics**
  - Admin APIs to manage content and users
  - Basic analytics: attempts, top-scores, per-quiz stats

- **Deployment-ready configuration**
  - Django settings prepared for Render (DATABASE_URL support, staticfiles via WhiteNoise)
  - Environment-driven CORS/CSRF configuration

---

## Important Views / API Endpoints (high-level)

> The names/paths below reflect the repo conventions. Update exact paths if you renamed them.

- **Auth**
  - `POST /api/v1/auth/register/` — Register a new user, set tokens as cookies
  - `POST /api/v1/auth/login/` — Login and set tokens + user cookie
  - `POST /api/v1/auth/logout/` — Clear cookies (no blacklist by default)
  - `POST /api/v1/auth/refresh/` — Optional refresh endpoint (middleware also handles refresh)
  - `POST /api/v1/auth/send-otp/` — Send OTP email (used for signup/verification)
  - `POST /api/v1/auth/verify-otp/` — Verify OTP

- **Quizzes**
  - `GET /api/v1/quiz/` — List quizzes
  - `POST /api/v1/quiz/create/` — Create a quiz
  - `GET /api/v1/quiz/<id>/` — Get quiz details
  - `POST /api/v1/quiz/<id>/attempt/` — Submit an attempt

- **User & Admin**
  - `GET /api/v1/user/me/` — Current user profile
  - Admin endpoints for user/quiz moderation (prefixed by `/api/v1/admin/`)

- **Real-time (Channels)**
  - WebSocket namespace(s) for `live-quiz` and `chat` with consumer handlers for join/leave/submit/message

---

## Middlewares

- **RefreshAccessMiddleware**
  - Reads `refresh_token` from HttpOnly cookie
  - If an Access header is missing or expired, creates a new access token from refresh token
  - Injects `Authorization: Bearer <access>` into `request.META` for DRF to authenticate
  - Saves refreshed tokens on `response` (sets access cookie, optionally rotates refresh tokens)

- **CSRF + Security Middlewares**
  - `CorsMiddleware` (must be first) to support cross-origin requests with credentials
  - `CsrfViewMiddleware` for CSRF protections on unsafe methods
  - WhiteNoise for static file serving

---

## Models (core)

- **User** — default Django user with profile fields (fullname, email)
- **Quiz** — metadata, author, published flag, time limits
- **Question** — linked to quiz, supports types (MCQ, TF, etc.), choices and correct answer
- **Attempt / Submission** — stored answers, score, timestamps
- **EmailOTP** — temporary OTP storage for verification

---

## Security & Best Practices Implemented

- **HttpOnly cookies** for tokens (prevents JS access) with environment-aware Secure & SameSite flags
- **Short-lived access tokens** and longer-lived refresh tokens
- **CORS whitelisting** for allowed frontend origins and credentials support
- **CSRF protections** enabled for unsafe methods
- Password hashing via Django's built-in mechanisms

---

## Deployment & Environment Notes

- Database: PostgreSQL (via `DATABASE_URL`) — `dj_database_url` used for parsing
- Static files: WhiteNoise for simple static hosting with `STATIC_ROOT` and `STATICFILES_STORAGE`
- Background/real-time: Redis channel layer for Django Channels
- Production specifics: `DEBUG=False` should enable `SESSION_COOKIE_SECURE=True` and `CSRF_COOKIE_SECURE=True` plus `SameSite=None`

---

## Useful local dev tips

- For cookie-based auth during local dev, run frontend and backend on the **same host** or use Vite proxy to avoid third-party cookie problems.
- Set `DEBUG=1` locally so helpers set `SameSite=Lax` and `secure=False` to permit HTTP localhost flows.
- Use console email backend when `DEBUG=True` to avoid SMTP failures during dev.

---

## What more can be added to the backend (recommended improvements)

### Short-term (priority)
- **Asynchronous email sending** (Celery / RQ / background jobs) to avoid blocking requests and worker crashes.
- **Robust retry and fallback** for SMTP (use transactional providers such as SendGrid/Mailgun) and add logging/alerting on send failures.
- **Automatic token rotation & optional blacklist support** (with token_blacklist app) for stronger refresh security.
- **Rate limiting** for endpoints susceptible to brute force (login, OTP) using `django-ratelimit` or DRF throttling.
- **Detailed auditing & logging** (attempts, suspicious activity, admin actions).

### Medium-term
- **Role-based access controls (RBAC)** for advanced admin/teacher/student roles and permissions.
- **Analytics microservice**: offload heavy analytics to a separate service or job that precomputes leaderboards and reports.
- **Export & reporting**: CSV / PDF export of quiz results, certificates generation, and scheduled reports.
- **API versioning** and formal API documentation (Swagger / Redoc)

### Long-term / Advanced
- **AI features**: auto-generate questions, intelligent difficulty calibration, cheating detection using behavior analytics.
- **Scalability hardening**: database read-replicas, auto-scaling workers, WebSocket routing and partitioning.
- **Enterprise features**: SSO (SAML / OIDC), multi-tenant support, advanced compliance & monitoring (GDPR/ISO).

---

## How to run (quick)

1. Create `.env` with required variables: `SECRET_KEY`, `DATABASE_URL`, `DEBUG`, email envs, `CORS_ALLOWED_ORIGINS`, etc.
2. `pip install -r requirements.txt` (use virtualenv)
3. `python manage.py migrate` and `python manage.py collectstatic --noinput`
4. `python manage.py runserver` (or run via `gunicorn` in production)
5. For Channels: run Redis and point `CHANNEL_LAYERS` to Redis host

---

## Final notes

This file should live at the root of the backend repository as `backend_INTRO.md` (or `README_BACKEND.md`). It gives maintainers and new contributors a clear on-ramp and highlights immediate next steps to harden and extend the project.

If you want, I can also:
- generate OpenAPI (Swagger) documentation for the current endpoints,
- produce a `docker-compose.yml` for local dev with Postgres + Redis + web service,
- or create a `CONTRIBUTING.md` with coding & deployment conventions.

