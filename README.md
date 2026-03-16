# PathMap

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.x-000000?logo=flask&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-ORM-CC2936)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14%2B-4169E1?logo=postgresql&logoColor=white)
![Gemini AI](https://img.shields.io/badge/Gemini_2.5_Flash-AI-8E75B2?logo=google&logoColor=white)
![Razorpay](https://img.shields.io/badge/Razorpay-Payments-3395FF?logo=razorpay&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Build](https://img.shields.io/badge/Build-Passing-brightgreen)

PathMap is a career pivot intelligence platform built for the Indian market. It helps professionals who feel stuck, threatened by automation, or pulled toward something new to make that transition with data instead of guesswork — combining a structured self-assessment engine, AI-powered feasibility analysis, real career pivot stories, and a marketplace for 1:1 coaching sessions with people who already made the leap.

---

## Table of Contents

- [The Problem (Why This Exists)](#the-problem-why-this-exists)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Architecture](#project-architecture)
- [Prerequisites](#prerequisites)
- [Installation and Setup](#installation-and-setup)
- [Environment Variables Reference](#environment-variables-reference)
- [Database Schema and Models](#database-schema-and-models)
- [API Routes / Endpoints Reference](#api-routes--endpoints-reference)
- [User Journey / How It Works](#user-journey--how-it-works)
- [Payment Integration](#payment-integration)
- [AI Integration](#ai-integration)
- [Security Architecture](#security-architecture)
- [Admin Panel](#admin-panel)
- [Testing](#testing)
- [Deployment](#deployment)
- [Seeded Data](#seeded-data)
- [Free vs Paid Features](#free-vs-paid-features)
- [Known Limitations and Future Improvements](#known-limitations-and-future-improvements)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgments](#acknowledgments)
- [Contact and Support](#contact-and-support)

---

## The Problem (Why This Exists)

Most career advice tools treat pivots like a job search problem. They show you job listings, let you update a resume, and call it guidance. But the real challenge in a career pivot is far earlier than that — it's the anxiety-inducing question of whether a move is even viable for you, given your specific skills, financial situation, time, and life constraints. Generic advice and optimistic LinkedIn posts don't answer that.

The Indian professional market makes this harder still. International career tools don't account for INR salary floors, the realities of pivoting in Bangalore versus Pune, or the income-change patterns that actually characterise transitions between Indian industries. A 30-something engineer in Mumbai considering a move into product management needs different data than someone making the same move in San Francisco.

PathMap was built to close this gap. It starts with a structured 5-module assessment that maps a user's actual skill set, work values, and real-world constraints — not aspirational answers, but honest ones. That profile then powers a skill transfer engine that calculates, skill by skill, which ones transfer directly to a target role, which are partially transferable through adjacent competencies, and which represent genuine gaps with estimated learning hours attached. A multi-dimensional feasibility score weighs in time availability, income floor, historical success data from real pivots, and available learning resources. The result is a picture of what a specific career move actually looks like for a specific person — not for a generic user archetype.

The platform also aggregates real career pivot stories submitted by professionals who made transitions themselves — what worked, what failed, unexpected discoveries, and advice they'd give. These aren't sanitised success stories. They include reversals and income drops because those are exactly the signals a rational decision-maker needs. Premium users can read an unlimited number of these stories, run unlimited analyses, book 1:1 shadow sessions with working professionals in their target field, and generate AI-enriched 90-day action plans. The entire system is designed to move a user from "I think I want to make a change" to "I have a specific plan and I know why it's viable."

---

## Features

### Authentication and Account Management
- User registration with email/password, with rate-limiting (5 sign-ups per hour per IP)
- Email verification via time-limited tokens (24-hour expiry) with resend capability
- Login with rate-limiting (10 attempts per 15 minutes) and account deactivation enforcement
- Secure password reset via timed single-use token (1-hour expiry, invalidated after use)
- "Remember me" login sessions lasting 365 days
- User-initiated GDPR data deletion request with admin execution workflow

### Onboarding
- 3-step guided onboarding: role category selection → specific role selection from seeded database → interests and challenge capture
- Pivot motivation capture from a defined set of motivations (feeling stuck, automation threat, burnout, etc.)
- Automatic Career Clarity Assessment creation on onboarding completion

### Career Clarity Assessment (5 Modules, ~22 Minutes)
- **Work Values Survey**: Rate 10 work values (autonomy, creativity, stability, income, impact, collaboration, learning, prestige, flexibility, social) to produce a ranked top-5 profile
- **Work Style Inventory**: 12 scenario-based questions across 4 dimensions (Execution vs Strategy, Collaboration vs Independence, Detail vs Big-Picture, Structured vs Adaptive)
- **Skill Confidence Assessment**: Rate 30 professional skills across 6 categories (Communication, Analytical, Technical, Creative, Leadership, Domain) on a 0–4 confidence scale
- **Life-Stage Constraints**: Capture income floor (INR), weekly hours available, timeline, and geographic flexibility
- **Career Vision**: 3 open-ended prompts with automated keyword-based theme extraction
- Sequential module gating (each module unlocks the next)
- Auto-save of in-progress responses via AJAX
- Retake capability that archives the current assessment and starts fresh
- AI-generated 200–250 word personalised career narrative on completion (Gemini 2.5 Flash)

### Skill Transfer Analysis
- Run analyses comparing any origin role to any target role in the seeded roles database
- Skill categorisation into three zones: direct match (confidence ≥ 3), partial match (confidence ≥ 1 or adjacent skill ≥ 2), and gap
- Adjacency-aware matching using a 30-skill adjacency map to find transferable skills
- Transfer score and gap score (0–100) based on importance-weighted skill requirements
- Estimated learning hours calculated from gap skill resource data
- Feasibility scoring across 5 dimensions: skill gap (weight 0.25), time feasibility (weight 0.20), financial feasibility (weight 0.20), historical success rate from real journeys (weight 0.20), and resource availability (weight 0.15)
- Feasibility narrative with per-dimension improvement suggestions
- What-if scenario engine: adjust timeline, hours/week, or income floor to see real-time feasibility changes
- Interactive skill sliders to adjust confidence ratings and recompute analysis live
- Compare up to 3 analyses side-by-side (target role, transfer score, feasibility score, skill breakdown)
- AI-powered job market insights for any target role using Gemini with live Google Search grounding
- Soft delete of analyses (marked unsaved, not database-deleted)
- Free tier: 1 analysis per calendar month; Premium: unlimited

### Pivot Planner (Premium)

**Decision Confidence Framework**
- Structured 5-step decision process saved per-analysis
- Step 1: Define the real decision, options, and what's at stake
- Step 2: Values alignment check — map top-5 values against each career option
- Step 3: Identify key assumptions per option and rate confidence (1–5)
- Step 4: 10/10/10 perspective test (how you'll feel in 10 days, 10 months, 10 years)
- Step 5: Commitment statement with AI-generated personalised accountability text
- Downloadable PDF decision summary (A4, multi-page, generated via ReportLab)

**90-Day Pivot Roadmap**
- Generated from skill gap analysis, linked to a specific saved analysis
- Configurable: start date, weekly hours commitment, priority balance across skills/networking/portfolio
- 13-week milestone structure with 4-week, 8-week, and 90-day checkpoint reviews
- Role-category-specific networking task templates (Technology, Finance, Healthcare, Creative, etc.)
- Role-category-specific portfolio task templates
- Priority-based task scheduling (high-importance gap skills assigned to weeks 1–6)
- AI-enriched descriptions for the top 3 skill tasks (Gemini 2.5 Flash)
- Task completion tracking with AJAX-based checkboxes
- Roadmap summary statistics: total tasks, estimated hours, task type breakdown
- Roadmap progress percentage updated in real-time on task completion

### Progress Tracking
- Weekly check-in form tied to the active roadmap (task completion, reflection, mood rating 1–5, obstacles)
- Mood-aware flash messages after check-in submission (different responses for low/medium/high mood)
- AI-generated reflection insight after each check-in (Gemini 2.5 Flash, max 80 words)
- Weekly streak counter (calendar-week based, resets if a week is missed)
- Activity heatmap covering the trailing 364 days (mood-level colour coding)
- Progress dashboard showing current week tasks, completion percentage, upcoming checkpoints
- Paginated progress history with week number, task count, and task title resolution
- Journal view filtered to entries with reflections, showing mood distribution statistics
- CSV export of full progress history (Premium only)
- Context-processor injected streak count visible across the authenticated UI

### Career Journey Explorer
- Browse community-submitted career pivot stories with full details (what worked, what failed, unexpected discoveries, advice)
- Filter by origin role, target role, outcome status (completed/in-progress/reversed), region, experience level, and timeline
- Sort by most recent, shortest timeline, longest timeline, highest income change, most viewed
- Aggregate statistics per filter set (total count, success rate, median timeline, average income change)
- Global statistics panel (total journeys, unique transitions, average timeline, income uplift percentage)
- Related journey recommendations on each detail page
- Transition statistics panel (success rate, income percentiles, average experience for that specific route)
- Monthly view limit tracking per user (5 views free, unlimited Premium)
- Journey submission form for authenticated users (pseudonym optional, consent required)
- Admin notification email on new submission
- Story pending state shown to submitter until published

### Shadow Sessions Marketplace
- Searchable marketplace of verified career pivot professionals offering 1:1 sessions
- Filter by role, industry, price range, minimum rating, and free-text search
- Sort by rating, price (low/high), most sessions completed, newest
- Provider profiles with bio, transition story, session description, verified badge, rating distribution
- Session booking with Razorpay order creation (one active booking limit per provider per user)
- Booking confirmation page and confirmation email to both booker and provider
- Provider scheduling: set session date/time and video link, triggers confirmation email to booker
- Session completion marking by either party
- Post-completion review form (rating 1–5, text, would-recommend, helped-decision flag)
- Provider rating recalculation on each new review
- Provider dashboard: booking list, review list, earnings summary (total, month-to-date, pending sessions)
- Provider application form (admin review workflow)
- Provider profile self-edit (bio, pricing, format, industries, booking URL, transition story)
- 12.5% platform commission on each session booking, automatic payout calculation
- Only Premium users can book sessions

### Resources Library
- Browseable learning resource library linked to skills in the database
- Filter by skill category, format type (video/text/project/course/bootcamp), cost tier, search term, minimum rating
- Recommended resources panel based on the user's highest-importance gap skills from their latest analysis
- Per-skill resource pages showing resources with provider, format, cost tier, estimated hours
- Resource bookmarking via AJAX (5 bookmarks free, unlimited Premium)
- My Bookmarks page with full resource details
- Free tier resource limiting: maximum 2 resources shown per skill
- Community resource submission form (any authenticated user can add a resource to the library)
- AJAX search endpoint for typeahead lookup by skill or resource name

### Blog
- Public-facing blog powered by admin-created BlogPost records
- Markdown content with safe rendering (bleach sanitisation + Bootstrap classes applied)
- Reading time estimation (word count / 200)
- Related posts suggestions on each article page
- Paginated post index (9 per page)

### User Profile and Settings
- Profile page with activity stats: assessment completion, saved analyses, journey submissions, check-ins, journeys read, sessions booked
- Profile completeness score (out of 100 points across key milestones)
- Settings page with tabbed sections: profile info, password change, notification preferences
- Notification preferences: weekly check-in emails, journey published, session updates, product updates, marketing
- Billing page: current plan, next renewal date, payment history (last 24 payments), total paid
- Cancel subscription (Razorpay cancel-at-cycle-end)
- Reactivate cancelled subscription
- Download invoices as CSV
- Full personal data export as JSON (assessments, analyses, roadmaps, progress entries, journeys, session bookings, payments)
- GDPR data deletion request (30-day execution window, admin-executed with data anonymisation)

### Admin Panel
- Overview dashboard: total users, premium users, 90-day active users, pending GDPR requests, 30-day revenue, revenue trend chart, booking trend chart, published/unpublished journey counts, active provider count, top 5 journeys by view count
- User management: view all users, toggle active/inactive, toggle admin flag, grant premium access
- Journey moderation: view all submissions, publish, unpublish, reject with reason
- Provider management: view active providers and pending applications, approve/reject applications (creates provider profile on approval)
- Session management: view all bookings, manually mark refunded
- Blog CMS: create blog posts with title, slug, content (Markdown), excerpt, tags, cover image URL, published flag
- GDPR panel: view pending deletion requests, execute deletions (anonymises user record and removes personal data)
- Revenue CSV export with invoice numbers, amounts, plan types, Razorpay IDs
- Admin audit log: records every admin action with IP address, action type, target type/ID, and details

---

## Tech Stack

**Backend**
- Python 3.11+ — primary language
- Flask 3.x — web framework using Application Factory Pattern and Blueprints
- Flask-SQLAlchemy — ORM for database models
- Flask-Migrate — Alembic-based database migrations
- Flask-Login — session management and user loading
- Flask-WTF — form handling and CSRF protection
- Flask-Mail — transactional email via SMTP
- Flask-Limiter — IP-based rate limiting on auth endpoints
- Werkzeug — password hashing (pbkdf2:sha256) and WSGI utilities
- itsdangerous — URL-safe timed tokens for email verification and password reset
- python-dotenv — environment variable loading from `.env`
- Gunicorn — production WSGI server

**Frontend**
- Jinja2 — server-rendered HTML templates
- Bootstrap (CDN, inferred from CSS class usage) — responsive UI components
- Bootstrap Icons — icon set used throughout the UI
- Vanilla JavaScript — assessment interactions, marketplace filters, Razorpay checkout flow, AJAX endpoints

**Database**
- SQLite — development default
- PostgreSQL 14+ (psycopg2-binary) — production target

**AI / ML**
- google-genai (Gemini 2.5 Flash) — dashboard welcome messages, career profile narratives, job market insights with live search grounding, decision commitment statements, roadmap task descriptions, reflection insights

**Payments**
- Razorpay — INR subscription payments (monthly ₹1,499 / annual ₹11,999) and shadow session one-time orders; webhook event processing for subscription lifecycle

**PDF Generation**
- ReportLab — multi-page A4 Decision Summary PDF (cover, decision clarity, values alignment, assumptions, 10/10/10, commitment)

**Email**
- Flask-Mail with SMTP — 12 email templates covering verification, welcome, password reset, premium welcome, subscription cancelled, payment failed, session booking confirmations, review invitations, session scheduling, GDPR deletion confirmation, admin notifications, provider application confirmations

**Markdown and Content**
- Python-Markdown — blog and admin content rendering with extensions: extra, codehilite, fenced_code, toc, nl2br, sane_lists, smarty
- bleach — HTML sanitisation for user-submitted content
- Pygments — syntax highlighting in code blocks
- markupsafe — safe Markup wrapping for Jinja2

**Security**
- Flask-WTF CSRF — token-based CSRF protection on all forms
- hmac / hashlib — Razorpay webhook signature verification and subscription payment verification
- Pillow — image handling dependency (imported, available for future image processing)

---

## Project Architecture

PathMap uses Flask's **Application Factory Pattern** with **Blueprints** to organise routes by domain. The factory function `create_app()` in `app/__init__.py` initialises all extensions, registers 14 blueprints, sets up custom Jinja2 filters and context processors, and ensures the database exists on first run.

Data flows from the browser through a blueprint route handler, which reads from and writes to SQLAlchemy models via the shared `db` session. Service modules (`app/services/`) contain all business logic — the skill transfer engine, feasibility calculator, AI calls, roadmap generator, email sender, and PDF builder — keeping routes thin. Jinja2 templates render server-side HTML; JavaScript handles only interactive elements (sliders, AJAX endpoints, Razorpay checkout).

```
PathMap-main/
├── .env.example
├── .gitignore
├── requirements.txt
├── run.py                          # App entry point, CLI commands (seed-db, create-admin)
├── seed_data/
│   └── seed.py                     # Production-quality seed runner
└── app/
    ├── __init__.py                 # Application factory, blueprint registration
    ├── config.py                   # Development, Production, Testing config classes
    ├── decorators.py               # Top-level premium_required decorator
    ├── extensions.py               # Extension instances (db, migrate, login_manager, etc.)
    ├── forms/
    │   ├── analysis_forms.py       # NewAnalysisForm
    │   ├── assessment_forms.py     # WorkValuesForm, WorkStyleForm, SkillsForm, ConstraintsForm, VisionForm
    │   ├── auth_forms.py           # SignupForm, LoginForm, ForgotPasswordForm, ResetPasswordForm, ContactForm, OnboardingForm
    │   ├── planner_forms.py        # RoadmapGenerationForm, DecisionStepForm
    │   ├── profile_forms.py        # UpdateProfileForm, ChangePasswordForm, NotificationPreferencesForm, GDPRDeletionForm, BlogPostForm, etc.
    │   ├── progress_forms.py       # CheckInForm, JourneySubmissionForm
    │   └── session_forms.py        # BookingForm, ProviderApplicationForm, ProviderEditForm, SessionReviewForm
    ├── models/
    │   ├── user.py                 # User model with token generation
    │   ├── assessment.py           # UserAssessment with 5-module tracking
    │   ├── analysis.py             # SkillTransferAnalysis
    │   ├── roadmap.py              # PivotRoadmap, ProgressEntry
    │   ├── journey.py              # Journey, JourneyView
    │   ├── role.py                 # Role, Skill, RoleSkillRequirement, LearningResource
    │   ├── session.py              # ShadowSessionProvider, SessionBooking, SessionReview, ProviderApplication, ResourceBookmark, BlogPost
    │   └── payment.py              # SubscriptionPayment, AdminAuditLog
    ├── routes/
    │   ├── auth.py                 # /auth/* — signup, login, logout, verify, reset
    │   ├── main.py                 # / — homepage, about, pricing, blog, contact, legal
    │   ├── onboarding.py           # /onboarding/* — 3-step onboarding flow
    │   ├── dashboard.py            # /dashboard/ — main dashboard, AI insight AJAX
    │   ├── assessment.py           # /assessment/* — 5-module assessment flow
    │   ├── analysis.py             # /skill-transfer/* — analysis CRUD and AJAX
    │   ├── planner.py              # /pivot-planner/* — decision framework and roadmap
    │   ├── progress.py             # /progress/* — check-ins, history, journal, export
    │   ├── journeys.py             # /journeys/* — explorer, detail, submit
    │   ├── sessions.py             # /shadow-sessions/* — marketplace, booking, provider
    │   ├── resources.py            # /resources/* — library, bookmarks, search
    │   ├── profile.py              # /profile-settings/* — profile, settings, billing, GDPR
    │   ├── payment.py              # /payment/* — Razorpay subscription and webhook
    │   ├── admin.py                # /admin/* — admin panel and moderation
    │   └── errors.py               # Custom error handlers (403, 404, 429, 500)
    ├── services/
    │   ├── ai_service.py           # All Gemini 2.5 Flash integrations
    │   ├── assessment_proc.py      # Assessment computation (values, workstyle, skills, vision profiles)
    │   ├── feasibility.py          # 5-dimension feasibility scoring engine
    │   ├── journey_query.py        # Journey search, statistics, view tracking
    │   ├── roadmap_gen.py          # 13-week roadmap generation and task assignment
    │   ├── skill_engine.py         # Skill transfer computation with adjacency matching
    │   ├── email_service.py        # All transactional email senders
    │   └── pdf_service.py          # ReportLab decision summary PDF builder
    ├── utils/
    │   ├── context_processors.py   # Assessment progress, streak, admin badge counts
    │   ├── decorators.py           # premium_required, admin_required, assessment_required, analysis_required
    │   ├── helpers.py              # format_inr, time_ago, truncate_text, log_admin_action
    │   └── markdown_renderer.py    # Markdown detection, conversion, sanitisation, Bootstrap class injection
    ├── static/
    │   ├── css/main.css
    │   └── js/
    │       ├── assessment.js
    │       ├── main.js
    │       ├── marketplace.js
    │       └── skill_map.js
    └── templates/
        ├── base.html / dashboard_base.html
        ├── components/             # navbar, footer, flash_messages
        ├── admin/                  # 9 admin templates
        ├── analysis/               # hub, new, detail, compare
        ├── assessment/             # hub + 5 module templates + results
        ├── auth/                   # login, signup, verify, forgot/reset password
        ├── dashboard/              # main dashboard
        ├── emails/                 # 13 transactional email templates
        ├── errors/                 # 403, 404, 429, 500
        ├── journeys/               # explorer, detail, submit
        ├── main/                   # homepage, about, pricing, blog, contact, legal, features, for-teams
        ├── onboarding/
        ├── planner/                # hub, decision, decision_summary, feasibility_detail, roadmap_form, roadmap_detail
        ├── profile/                # profile, settings, billing
        ├── progress/               # dashboard, check_in, history, journal
        ├── resources/              # library, skill_resources, category, create, bookmarks
        └── sessions/               # marketplace, provider_profile, book, my_bookings, provider_dashboard, etc.
```

---

## Prerequisites

Before setting up PathMap, you need the following installed and configured:

- **Python 3.11 or higher** — the codebase uses modern type annotations and standard library features
- **pip** — Python package installer, comes with Python
- **Git** — for cloning the repository
- **PostgreSQL 14+** (production) — psycopg2-binary is used as the adapter; SQLite works for local development without any additional setup
- **Google AI Studio account** — required to obtain a `GEMINI_API_KEY`; all AI features depend on the Gemini 2.5 Flash model
- **Razorpay account** — required to process subscription payments and session bookings; you need Key ID, Key Secret, and Webhook Secret from the Razorpay Dashboard
- **SMTP email service** — any SMTP provider works (Gmail, Mailtrap for development, SendGrid, etc.); you need SMTP hostname, port, username, and password

---

## Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/PathMap.git
cd PathMap
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate       # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs Flask, SQLAlchemy, Flask-Migrate, Flask-Login, Flask-WTF, Flask-Mail, Flask-Limiter, WTForms, email-validator, Werkzeug, python-dotenv, Gunicorn, psycopg2-binary, razorpay, google-genai, reportlab, itsdangerous, Pillow, Markdown, bleach, and pygments.

### 4. Configure Environment Variables

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

Open `.env` and set every variable. See the [Environment Variables Reference](#environment-variables-reference) for what each one does and how to obtain it.

### 5. Initialise the Database

For a fresh installation, the app auto-creates tables on first run. To do this explicitly:

```bash
flask --app run.py create-db
```

To use Flask-Migrate for tracked migrations instead:

```bash
flask --app run.py db init
flask --app run.py db migrate -m "initial schema"
flask --app run.py db upgrade
```

### 6. Seed the Database

This step is strongly recommended. The seed script populates roles, skills, role-skill requirements, learning resources, sample career journeys, sample session providers, and blog posts — the data the core product features depend on.

```bash
flask --app run.py seed-db
```

The seeder is idempotent; running it again updates existing records rather than creating duplicates. See [Seeded Data](#seeded-data) for a full breakdown of what gets created.

### 7. Create the Admin User (Optional — Seed Does This Automatically)

If you skipped seeding, create the admin user manually:

```bash
flask --app run.py create-admin
```

This creates `admin@pathmap.in` with password `Admin@PathMap2026!`.

### 8. Run the Development Server

```bash
python run.py
```

Or using the Flask CLI:

```bash
flask --app run.py run --debug
```

### 9. Access the Application

Open your browser at [http://localhost:5000](http://localhost:5000).

Log in as admin at `/auth/login` with `admin@pathmap.in` / `Admin@PathMap2026!`, or register a new account and follow the email verification flow.

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `FLASK_ENV` | Yes | `development` | Set to `development` or `production`. Controls debug mode, HTTPS-only cookies, and CSRF strictness. |
| `SECRET_KEY` | Yes | — | Random string, minimum 32 characters. Used to sign sessions and CSRF tokens. Generate with `python -c "import secrets; print(secrets.token_hex(32))"`. |
| `DATABASE_URL` | Yes | `sqlite:///pathmap_dev.db` | SQLAlchemy connection string. For PostgreSQL: `postgresql://user:password@host:5432/pathmap`. |
| `MAIL_SERVER` | Yes | `smtp.gmail.com` | SMTP server hostname. Use `smtp.mailtrap.io` for development to catch emails without sending them. |
| `MAIL_PORT` | Yes | `587` | SMTP port. Use 587 for TLS (recommended) or 465 for SSL. |
| `MAIL_USE_TLS` | Yes | `True` | Set to `True` for port 587 STARTTLS. |
| `MAIL_USERNAME` | Yes | — | SMTP authentication username (usually your email address or API key). |
| `MAIL_PASSWORD` | Yes | — | SMTP authentication password or app-specific password. |
| `MAIL_DEFAULT_SENDER` | Yes | `noreply@pathmap.in` | The "From" address shown on all outgoing emails. |
| `ADMIN_EMAIL` | Yes | `admin@pathmap.in` | Receives copies of contact form submissions and provider application alerts. |
| `ADMIN_ALERT_EMAIL` | Yes | `admin-alert@pathmap.in` | Receives high-priority alerts (new journey submissions, GDPR deletion requests). |
| `RAZORPAY_KEY_ID` | Yes | — | Your Razorpay API Key ID. Find this in Razorpay Dashboard → Settings → API Keys. Use `rzp_test_...` prefix for testing. |
| `RAZORPAY_KEY_SECRET` | Yes | — | Your Razorpay API Key Secret. Keep this private — never expose it in client-side code. |
| `RAZORPAY_WEBHOOK_SECRET` | Yes | — | The secret you configure in Razorpay Dashboard → Webhooks when setting up the `/payment/webhook` endpoint. |
| `RAZORPAY_MONTHLY_PRICE_PAISE` | No | `149900` | Price in paise (1 paise = 1/100 INR). Default is ₹1,499. |
| `RAZORPAY_ANNUAL_PRICE_PAISE` | No | `1199900` | Price in paise. Default is ₹11,999. |
| `GEMINI_API_KEY` | Yes | — | API key from Google AI Studio (https://aistudio.google.com). Required for all AI features — dashboard welcome, profile narrative, market insights, roadmap enrichment, reflection insights. |
| `BASE_URL` | Yes | `http://localhost:5000` | Used to build absolute URLs in emails. Set to your production domain (e.g., `https://pathmap.in`). |

---

## Database Schema and Models

### `users`
Stores registered user accounts. Central table with foreign-key relationships across the entire schema.

| Field | Type | Description |
|---|---|---|
| `id` | Integer PK | Auto-incrementing primary key |
| `email` | String(255), unique | Login identifier, normalised to lowercase |
| `password_hash` | String(255) | pbkdf2:sha256 hash with 16-byte salt |
| `first_name` | String(100) | Display name; falls back to email prefix if not set |
| `is_verified` | Boolean | Email verification flag; login blocked until True |
| `is_premium` | Boolean | Active premium subscription flag |
| `subscription_tier` | String(50) | `free`, `monthly`, `annual`, or `admin_granted` |
| `subscription_expires` | DateTime | Premium access expiry; NULL means no expiry (admin-granted) |
| `razorpay_customer_id` | String(100) | Razorpay customer reference |
| `razorpay_subscription_id` | String(100) | Active subscription ID used for cancellation/reactivation |
| `subscription_cancel_requested` | Boolean | True if cancellation is pending at cycle end |
| `onboarding_complete` | Boolean | Controls post-login redirect to onboarding vs dashboard |
| `current_role_id` | Integer | User's selected current role (nullable) |
| `years_experience` | Integer | Years of professional experience captured in onboarding |
| `pivot_motivation` | String(300) | Motivation code (e.g., `feeling_stuck`, `burnout`) |
| `is_admin` | Boolean | Admin panel access flag |
| `is_journey_provider` | Boolean | Set to True when a provider application is approved |
| `is_active` | Boolean | Account active flag; inactive accounts cannot log in |
| `gdpr_deletion_requested` | Boolean | GDPR deletion request flag |
| `notification_preferences` | JSON | Dict of boolean notification channel preferences |

### `user_assessments`
Stores one assessment per user at a time (the current one), with historical assessments retained as `is_current=False`.

| Field | Type | Description |
|---|---|---|
| `id` | Integer PK | |
| `user_id` | Integer FK → users | |
| `is_current` | Boolean | Only one assessment per user should be current |
| `values_data` | JSON | Ratings, top-5 values, ranked list |
| `values_completed` | Boolean | Gate for next module |
| `workstyle_data` | JSON | Question responses, dimension scores, dominant/secondary style |
| `workstyle_completed` | Boolean | |
| `skills_data` | JSON | Skill ratings dict and category averages |
| `skills_completed` | Boolean | |
| `constraints_data` | JSON | income_floor (INR), hours_per_week, timeline_months, geographic_flexibility |
| `constraints_completed` | Boolean | |
| `vision_data` | JSON | Three vision prompt responses and extracted themes |
| `vision_completed` | Boolean | |
| `profile_summary` | JSON | Aggregated profile including AI narrative |
| `completed_at` | DateTime | When all 5 modules were completed |

### `skill_transfer_analyses`
One record per role comparison run by a user.

| Field | Type | Description |
|---|---|---|
| `id` | Integer PK | |
| `user_id` | Integer FK → users | |
| `origin_role_id` | Integer FK → roles | |
| `target_role_id` | Integer FK → roles | |
| `user_skill_overrides` | JSON | Skill name → rating overrides from sliders |
| `transfer_score` | Float | 0–100, weighted proportion of transferable skills |
| `gap_score` | Float | 100 minus transfer_score |
| `direct_skills` | JSON | Skills at confidence ≥ 3 with importance weights |
| `partial_skills` | JSON | Skills at confidence 1–2 or adjacent match |
| `gap_skills` | JSON | Missing skills with importance, learning resources |
| `estimated_learning_hours` | Float | Sum of top learning resource hours for gap skills |
| `feasibility_score` | Float | 0–100 composite score |
| `feasibility_breakdown` | JSON | Per-dimension score and weight |
| `feasibility_narrative` | Text | Plain-English explanation of strongest/weakest dimensions |
| `is_saved` | Boolean | False = soft-deleted |
| `decision_data` | JSON | 5-step decision framework responses |
| `decision_completed` | Boolean | All 5 steps completed |

### `pivot_roadmaps`
One active roadmap per user; older ones set to `is_active=False` when a new one is generated.

| Field | Type | Description |
|---|---|---|
| `id` | Integer PK | |
| `user_id` | Integer FK → users | |
| `target_role_id` | Integer FK → roles | |
| `analysis_id` | Integer FK → skill_transfer_analyses | The analysis this roadmap is based on |
| `start_date` | Date | When the 90-day clock starts |
| `hours_per_week` | Integer | User's committed weekly time budget |
| `priority_balance` | JSON | `{skills: %, network: %, portfolio: %}` summing to 100 |
| `milestones` | JSON | Array of 13 week objects, each with tasks array |
| `overall_progress_pct` | Float | Recomputed on each check-in |
| `is_active` | Boolean | Only one active roadmap per user |

### `progress_entries`
One entry per check-in event, tied to a roadmap.

| Field | Type | Description |
|---|---|---|
| `id` | Integer PK | |
| `user_id` | Integer FK → users | |
| `roadmap_id` | Integer FK → pivot_roadmaps | |
| `entry_date` | Date | Check-in date |
| `tasks_completed` | JSON | Array of task ID strings |
| `reflection` | Text | User's weekly reflection text |
| `mood_rating` | Integer | 1 (struggling) to 5 (great) |
| `obstacles_noted` | Text | Free-text obstacle description |

### `journeys`
Community-submitted real career pivot stories.

| Field | Type | Description |
|---|---|---|
| `id` | Integer PK | |
| `submitter_user_id` | Integer FK → users | Nullable; set to NULL on GDPR deletion |
| `origin_role_id` | Integer FK → roles | |
| `target_role_id` | Integer FK → roles | |
| `outcome_status` | String(50) | `completed`, `in_progress`, or `reversed` |
| `timeline_months` | Integer | Total time from decision to landing in new role |
| `preparation_months` | Integer | Time spent preparing before first application |
| `income_change_pct` | Float | Positive/negative percentage income change |
| `summary` | Text | Narrative overview |
| `what_worked` | Text | What the person would do again |
| `what_failed` | Text | What they wish they'd done differently |
| `unexpected_discoveries` | Text | Surprises, good or bad |
| `advice_to_others` | Text | Direct advice to someone considering this pivot |
| `total_cost_inr` | Float | Total out-of-pocket cost for courses, tools, etc. |
| `geographic_region` | String(100) | City or region |
| `pseudonym` | String(100) | Optional display name; anonymous if null |
| `is_published` | Boolean | Admin-moderated publication gate |
| `rejection_reason` | Text | Admin rejection feedback |

### `journey_views`
Tracks monthly view counts per user for enforcing the 5-view free tier limit.

| Field | Type | Description |
|---|---|---|
| `user_id` | Integer FK → users | |
| `journey_id` | Integer FK → journeys | |
| `view_month` | Integer | Calendar month (1–12) |
| `view_year` | Integer | Calendar year |

### `roles`
Career roles used as origin and target in analyses and journeys.

| Field | Type | Description |
|---|---|---|
| `id` | Integer PK | |
| `title` | String(200) | Role display name (e.g., "Product Manager") |
| `category` | String(100) | Industry/function grouping (e.g., "Product", "Finance") |
| `sub_category` | String(100) | Optional sub-grouping |
| `is_active` | Boolean | Only active roles appear in selection dropdowns |

### `skills`
Professional skills, each belonging to one category.

| Field | Type | Description |
|---|---|---|
| `id` | Integer PK | |
| `name` | String(200) | Skill display name (e.g., "Python Programming") |
| `category` | String(100) | Broad category (Communication, Analytical, Technical, etc.) |
| `description` | Text | One-line description used in assessment UI |

### `role_skill_requirements`
Junction table linking roles to the skills they require, with importance weights.

| Field | Type | Description |
|---|---|---|
| `role_id` | Integer FK → roles | |
| `skill_id` | Integer FK → skills | |
| `importance_weight` | Float | 0.0–1.0 scale; drives transfer/gap score weighting |
| `transfer_type` | String(50) | Classification of how the skill type transfers |

### `learning_resources`
Curated learning resources linked to specific skills.

| Field | Type | Description |
|---|---|---|
| `id` | Integer PK | |
| `skill_id` | Integer FK → skills | |
| `title` | String(300) | Resource title |
| `provider` | String(200) | Platform or publisher (e.g., "Coursera", "Udemy") |
| `format` | String(100) | `video`, `text`, `project`, `course`, or `bootcamp` |
| `cost_tier` | String(50) | `free`, `low_cost`, or `premium` |
| `estimated_hours` | Float | Time to complete |
| `url` | String(500) | Direct link to resource |
| `quality_rating` | Float | 0.0–5.0 editorial quality score |

### `shadow_session_providers`
Profiles for approved session providers in the marketplace.

| Field | Type | Description |
|---|---|---|
| `user_id` | Integer FK → users, unique | One provider profile per user |
| `current_role_id` | Integer FK → roles | The role the provider now works in |
| `display_name` | String(100) | Public name shown in marketplace |
| `bio` | Text | Provider background |
| `transition_story` | Text | Their personal pivot story |
| `price_inr` | Numeric(10,2) | Session price in INR |
| `booking_url` | String(500) | External scheduling link (Calendly, etc.) |
| `is_verified` | Boolean | Admin verification gate; only verified providers appear |
| `avg_rating` | Numeric(3,2) | Recalculated on each new review |
| `total_sessions` | Integer | Incremented on each paid booking |
| `total_reviews` | Integer | Incremented on each submitted review |

### `session_bookings`
Payment and lifecycle record for each session booking.

| Field | Type | Description |
|---|---|---|
| `provider_id` | Integer FK → shadow_session_providers | |
| `booker_user_id` | Integer FK → users | Nullified on GDPR deletion |
| `amount_inr` | Numeric(10,2) | Provider's listed price at booking time |
| `commission_inr` | Numeric(10,2) | Platform 12.5% fee |
| `provider_payout_inr` | Numeric(10,2) | Amount after commission |
| `razorpay_order_id` | String(200) | Razorpay order reference |
| `razorpay_payment_id` | String(200) | Confirmed payment ID |
| `razorpay_signature` | String(500) | Verification signature |
| `status` | String(50) | `pending`, `paid`, `session_scheduled`, `session_completed`, `refund_requested`, `refunded`, `disputed` |

### `session_reviews`
Post-session reviews left by bookers.

| Field | Type | Description |
|---|---|---|
| `provider_id` | Integer FK → shadow_session_providers | |
| `reviewer_user_id` | Integer FK → users | |
| `booking_id` | Integer FK → session_bookings, unique | One review per booking |
| `rating` | Integer | 1–5 (enforced by DB CHECK constraint) |
| `review_text` | Text | Written review |
| `would_recommend` | Boolean | |
| `session_helped_decision` | Boolean | Whether the session helped the user decide |

### `provider_applications`
Applications submitted by users who want to become session providers.

| Field | Type | Description |
|---|---|---|
| `user_id` | Integer FK → users | |
| `application_status` | String(50) | `pending`, `approved`, or `rejected` |
| `proposed_display_name`, `proposed_bio`, `proposed_session_description` | Text | Application content reviewed by admin |
| `proposed_price_inr` | Numeric(10,2) | Requested pricing |
| `why_good_provider` | Text | Motivation statement |
| `reviewed_by_admin_id` | Integer FK → users | Admin who processed the application |

### `resource_bookmarks`
Tracks which resources each user has bookmarked. Unique per (user, resource) pair.

### `subscription_payments`
Financial record for each recurring charge captured via webhook.

| Field | Type | Description |
|---|---|---|
| `razorpay_payment_id` | String(200), unique | Prevents duplicate processing |
| `razorpay_subscription_id` | String(200) | Links back to subscription lifecycle |
| `amount_inr` | Numeric(10,2) | Amount in INR |
| `plan_type` | String(50) | `monthly` or `annual` |
| `payment_status` | String(50) | `captured` |

### `admin_audit_logs`
Immutable record of every admin action.

| Field | Type | Description |
|---|---|---|
| `admin_user_id` | Integer FK → users | Who performed the action |
| `action_type` | String(100) | e.g., `publish_journey`, `approve_provider_application` |
| `target_type` | String(100) | e.g., `Journey`, `User` |
| `target_id` | Integer | ID of the affected record |
| `ip_address` | String(45) | Admin's IP at action time |

### `blog_posts`
Admin-authored blog content.

| Field | Type | Description |
|---|---|---|
| `title` | String(300) | Post title |
| `slug` | String(300), unique | URL path segment (auto-generated from title if not set) |
| `content` | Text | Markdown or HTML content; auto-detected for rendering |
| `is_published` | Boolean | Controls public visibility |
| `tags` | String(500) | Comma-separated tag string |

---

## API Routes / Endpoints Reference

### Main Blueprint (`/`)

| Method | Path | Access | Description |
|---|---|---|---|
| GET | `/` | Public | Homepage with 2 journey previews and featured role list |
| GET | `/about` | Public | About page |
| GET | `/how-it-works` | Public | Product explainer |
| GET | `/pricing` | Public | Pricing page with Razorpay key and plan prices |
| GET | `/blog` | Public | Blog index, paginated 9 per page |
| GET | `/blog/<slug>` | Public | Individual blog post with related posts |
| GET | `/contact` | Public | Contact form |
| POST | `/contact` | Public | Submit contact form, sends email |
| GET | `/features` | Public | Features overview page |
| GET | `/for-teams` | Public | Teams landing page |
| GET | `/privacy` | Public | Privacy policy |
| GET | `/terms` | Public | Terms of service |

### Auth Blueprint (`/auth`)

| Method | Path | Access | Limit | Description |
|---|---|---|---|---|
| GET/POST | `/auth/signup` | Public | 5/hour | Register new account, sends verification email |
| GET/POST | `/auth/login` | Public | 10/15min | Login; redirects to onboarding if incomplete |
| GET | `/auth/logout` | Authenticated | — | Clears session |
| GET | `/auth/verify/<token>` | Public | — | Confirms email (24h token), sends welcome email |
| GET/POST | `/auth/verify-pending` | Public | — | Resend verification email |
| GET/POST | `/auth/forgot-password` | Public | 3/hour | Send password reset email (user-enumeration safe) |
| GET/POST | `/auth/reset/<token>` | Public | — | Reset password (1h single-use token) |

### Onboarding Blueprint (`/onboarding`)

| Method | Path | Access | Description |
|---|---|---|---|
| GET | `/onboarding/` | Authenticated | Step 1: role category and motivation |
| POST | `/onboarding/step/1` | Authenticated | Save step 1, redirect to step 2 |
| GET | `/onboarding/step/2` | Authenticated | Step 2: specific role selection |
| POST | `/onboarding/step/2` | Authenticated | Save role, redirect to step 3 |
| GET | `/onboarding/step/3` | Authenticated | Step 3: interests and challenge |
| POST | `/onboarding/complete` | Authenticated | Complete onboarding, create assessment, redirect to assessment hub |

### Dashboard Blueprint (`/dashboard`)

| Method | Path | Access | Description |
|---|---|---|---|
| GET | `/dashboard/` | Authenticated | Main dashboard with AI welcome, quick actions, roadmap status, streak |
| POST | `/dashboard/ai-insight` | Authenticated | AJAX: AI career insight (3/day free, unlimited Premium) |

### Assessment Blueprint (`/assessment`)

| Method | Path | Access | Description |
|---|---|---|---|
| GET | `/assessment/` | Authenticated | Assessment hub showing 5 module cards with progress |
| GET/POST | `/assessment/values` | Authenticated | Work Values Survey (10 sliders) |
| GET/POST | `/assessment/workstyle` | Authenticated | Work Style Inventory (12 questions) |
| GET/POST | `/assessment/skills` | Authenticated | Skill Confidence Assessment (30 skills) |
| GET/POST | `/assessment/constraints` | Authenticated | Life-Stage Constraints form |
| GET/POST | `/assessment/vision` | Authenticated | Career Vision (3 prompts) |
| POST | `/assessment/autosave` | Authenticated | AJAX: Auto-save in-progress module data |
| GET | `/assessment/results` | Authenticated | Full profile results with AI narrative |
| POST | `/assessment/retake` | Authenticated | Archive current assessment, start fresh |

### Skill Transfer Analysis Blueprint (`/skill-transfer`)

| Method | Path | Access | Description |
|---|---|---|---|
| GET | `/skill-transfer/` | Authenticated | Analysis hub: saved analyses, monthly usage counter |
| GET | `/skill-transfer/new` | Authenticated | New analysis form: origin + target role selection |
| POST | `/skill-transfer/new` | Authenticated | Create analysis (enforces 1/month free limit) |
| GET | `/skill-transfer/<id>` | Authenticated/Owner | Analysis detail: skills breakdown, feasibility, sliders |
| POST | `/skill-transfer/<id>/adjust` | Authenticated/Owner | AJAX: Recompute analysis with skill slider override |
| GET | `/skill-transfer/compare` | Authenticated | Compare up to 3 analyses side-by-side |
| POST | `/skill-transfer/<id>/market-insights` | Authenticated/Owner | AJAX: Fetch AI market insights for target role |
| POST | `/skill-transfer/<id>/delete` | Authenticated/Owner | Soft-delete analysis |
| POST | `/skill-transfer/<id>/what-if` | Authenticated/Owner | AJAX: Recompute feasibility with what-if overrides |

### Pivot Planner Blueprint (`/pivot-planner`)

| Method | Path | Access | Description |
|---|---|---|---|
| GET | `/pivot-planner/` | Authenticated | Planner hub: tool cards with lock/unlock status |
| GET | `/pivot-planner/decision` | Premium + Analysis | Decision framework: 5-step process |
| POST | `/pivot-planner/decision/step/<n>` | Premium | Save decision step (1–5), redirects to next step |
| GET | `/pivot-planner/decision/summary/<id>` | Premium/Owner | Decision summary view |
| GET | `/pivot-planner/decision/summary/<id>/download` | Premium/Owner | Download decision summary as PDF |
| GET | `/pivot-planner/feasibility/<id>` | Authenticated/Owner | Feasibility score detail breakdown |
| GET | `/pivot-planner/roadmap/new` | Premium + Analysis | Roadmap generation form |
| POST | `/pivot-planner/roadmap/new` | Premium | Generate 90-day roadmap |
| GET | `/pivot-planner/roadmap/<id>` | Premium/Owner | Roadmap detail: 13 weeks, task completion |
| POST | `/pivot-planner/roadmap/<id>/complete-tasks` | Premium/Owner | AJAX: Mark tasks complete |

### Progress Blueprint (`/progress`)

| Method | Path | Access | Description |
|---|---|---|---|
| GET | `/progress/` | Authenticated | Progress dashboard: heatmap, streak, current week tasks |
| GET | `/progress/check-in` | Authenticated | Weekly check-in form |
| POST | `/progress/check-in` | Authenticated | Submit check-in; triggers AI reflection insight |
| GET | `/progress/history` | Authenticated | Paginated entry history with task details |
| GET | `/progress/journal` | Authenticated | Reflection-only journal view with mood distribution |
| GET | `/progress/export` | Premium | Download full progress history as CSV |

### Journeys Blueprint (`/journeys`)

| Method | Path | Access | Description |
|---|---|---|---|
| GET | `/journeys/` | Authenticated | Filterable explorer; tracks monthly free view count |
| GET | `/journeys/<id>` | Authenticated | Journey detail (enforces 5-view free monthly limit) |
| GET | `/journeys/submit` | Authenticated | Submission form |
| POST | `/journeys/submit` | Authenticated | Submit journey for admin review |

### Shadow Sessions Blueprint (`/shadow-sessions`)

| Method | Path | Access | Description |
|---|---|---|---|
| GET | `/shadow-sessions/` | Authenticated | Marketplace with filters |
| GET | `/shadow-sessions/<id>` | Authenticated | Provider profile with reviews |
| GET | `/shadow-sessions/book/<id>` | Premium | Booking page with price and commission breakdown |
| POST | `/shadow-sessions/book/<id>/create-order` | Premium | AJAX: Create Razorpay order, insert pending booking |
| POST | `/shadow-sessions/book/<id>/verify-payment` | Authenticated | AJAX: Verify payment signature, confirm booking |
| GET | `/shadow-sessions/booking/<id>/confirmation` | Authenticated/Owner | Booking confirmation page |
| GET | `/shadow-sessions/my-bookings` | Authenticated | User's booking list with provider view |
| GET/POST | `/shadow-sessions/book/<booking_id>/review` | Authenticated/Owner | Leave review for completed session |
| GET/POST | `/shadow-sessions/become-provider` | Authenticated | Provider application form |
| GET | `/shadow-sessions/provider/dashboard` | Authenticated/Provider | Provider earnings and booking management |
| GET/POST | `/shadow-sessions/provider/edit` | Authenticated/Provider | Edit provider profile |
| POST | `/shadow-sessions/booking/<id>/mark-complete` | Authenticated | AJAX: Mark session complete; triggers review invitation email |
| POST | `/shadow-sessions/booking/<id>/schedule` | Provider | AJAX: Set session time and join link |

### Resources Blueprint (`/resources`)

| Method | Path | Access | Description |
|---|---|---|---|
| GET | `/resources/` | Authenticated | Resource library with gap-skill recommendations |
| GET/POST | `/resources/create` | Authenticated | Add a new learning resource |
| GET | `/resources/skill/<id>` | Authenticated | Resources for a specific skill |
| GET | `/resources/category/<name>` | Authenticated | All skills and resources in a category |
| POST | `/resources/bookmark/<id>` | Authenticated | AJAX: Toggle bookmark (returns bookmarked status) |
| GET | `/resources/bookmarks` | Authenticated | User's bookmarked resources |
| GET | `/resources/search` | Authenticated | AJAX: Typeahead search, returns JSON |

### Profile Blueprint (`/profile-settings`)

| Method | Path | Access | Description |
|---|---|---|---|
| GET | `/profile-settings/profile` | Authenticated | Profile page with activity stats and completeness score |
| GET | `/profile-settings/settings` | Authenticated | Tabbed settings: profile, password, notifications, privacy |
| POST | `/profile-settings/settings/update-profile` | Authenticated | Update name, role, experience |
| POST | `/profile-settings/settings/change-password` | Authenticated | Change password (requires current password) |
| POST | `/profile-settings/settings/update-notifications` | Authenticated | Save notification preferences |
| GET | `/profile-settings/billing` | Authenticated | Subscription status, payment history |
| POST | `/profile-settings/settings/request-data-export` | Authenticated | Download personal data as JSON |
| POST | `/profile-settings/settings/request-gdpr-deletion` | Authenticated | Request account deletion |
| POST | `/profile-settings/admin/execute-gdpr-deletion/<id>` | Admin | Execute anonymisation and deletion |

### Payment Blueprint (`/payment`)

| Method | Path | Access | Description |
|---|---|---|---|
| POST | `/payment/create-subscription` | Authenticated | Create Razorpay subscription, returns subscription ID |
| POST | `/payment/verify-subscription` | Authenticated | Verify payment signature, activate premium |
| POST | `/payment/webhook` | Public (CSRF-exempt) | Handle Razorpay webhook events |
| POST | `/payment/cancel-subscription` | Authenticated | Cancel subscription at cycle end |
| POST | `/payment/reactivate-subscription` | Authenticated | Resume cancelled subscription |
| GET | `/payment/download-invoices` | Authenticated | Download payment history as CSV |

### Admin Blueprint (`/admin`)

| Method | Path | Access | Description |
|---|---|---|---|
| GET | `/admin/` | Admin | Dashboard: stats, charts, pending counts |
| GET | `/admin/users` | Admin | User list with counts |
| POST | `/admin/users/<id>/toggle-active` | Admin | Toggle user active status |
| POST | `/admin/users/<id>/toggle-admin` | Admin | Toggle admin flag |
| POST | `/admin/users/<id>/grant-premium` | Admin | Grant permanent premium access |
| GET | `/admin/journeys` | Admin | All journey submissions |
| POST | `/admin/journeys/<id>/publish` | Admin | Publish a journey |
| POST | `/admin/journeys/<id>/unpublish` | Admin | Unpublish a journey |
| POST | `/admin/journeys/<id>/reject` | Admin | Reject with reason |
| GET | `/admin/providers` | Admin | Active providers and pending applications |
| POST | `/admin/providers/applications/<id>/approve` | Admin | Approve application, create provider profile |
| POST | `/admin/providers/applications/<id>/reject` | Admin | Reject with reason |
| GET | `/admin/sessions` | Admin | All session bookings |
| POST | `/admin/sessions/<id>/mark-refunded` | Admin | Mark booking refunded |
| GET/POST | `/admin/blog` | Admin | Blog CMS: list posts, create new post |
| GET | `/admin/gdpr` | Admin | Pending GDPR deletion requests |
| GET | `/admin/revenue/export` | Admin | Download all payments as CSV |
| GET | `/admin/audit-log` | Admin | Last 200 admin audit log entries |

---

## User Journey / How It Works

A new user lands on the homepage and reads about PathMap, then signs up with their email address and a password. They receive a verification email and click the link to confirm their account. On their first login, they're routed through a 3-step onboarding: selecting their current role category (Technology, Finance, Healthcare, etc.), picking their specific current role from the seeded database, and answering why they're considering a pivot and what their biggest challenge is.

After onboarding, they land on the Career Clarity Assessment hub. The 5 modules must be completed in sequence, each building on the last. They spend about 22 minutes rating their work values, answering work-style scenarios, rating their confidence across 30 skills, setting their income floor and time constraints, and describing their ideal career future in three open-ended prompts. When they complete the fifth module, Gemini generates a personalised 200-word career narrative that reflects their values, style, strongest skill category, and vision themes.

With a completed profile, they can run a Skill Transfer Analysis. They select their current role as the origin and pick one or more target roles. The analysis runs immediately: the skill engine calculates direct matches, partial transfers via adjacent competencies, and genuine gaps, then the feasibility engine scores the transition across five dimensions. They can adjust skill confidence using interactive sliders, run what-if scenarios (what happens if I increase my weekly hours?), and compare up to three target roles side-by-side.

Free users can run one analysis per calendar month. At this point, they typically encounter the Premium paywall and can upgrade for ₹1,499/month (₹11,999/year). On the Premium plan, they get unlimited analyses and access to the Pivot Planner.

In the Pivot Planner, they work through a 5-step Decision Confidence Framework — defining the real decision, checking value alignment, identifying key assumptions with confidence ratings, applying a 10/10/10 temporal perspective test, and writing a commitment statement. Gemini generates a personalised accountability statement at the end. They can download the complete decision summary as a branded PDF to keep as a private document.

Then they generate a 90-Day Pivot Roadmap. They choose which saved analysis to base it on, set a start date, their weekly time budget, and how to balance effort across skill-building, networking, and portfolio work. The roadmap engine creates a 13-week plan with role-specific tasks. The top skill tasks get AI-enriched descriptions from Gemini. Each Sunday, they log a weekly check-in: which tasks they completed, a reflection on the week, their mood, and any obstacles. Gemini responds with a 2-3 sentence personalised insight.

Throughout the journey, they can browse real career pivot stories filtered to their specific transition, book a 1:1 shadow session with a professional who already made their target move, and access the curated resource library with courses and guides mapped to their skill gaps.

---

## Payment Integration

PathMap uses **Razorpay** for both recurring subscription payments and one-time session bookings. The payment currency is always INR.

### Subscription Flow

The subscription system uses Razorpay's subscription API (not simple orders). Before accepting any payments, you must create two plan records in the Razorpay Dashboard — a monthly plan at ₹1,499 and an annual plan at ₹11,999 — and store the generated plan IDs in `RAZORPAY_MONTHLY_PLAN_ID` and `RAZORPAY_ANNUAL_PLAN_ID`. The app will auto-create plans on the fly if these are missing or if the amount doesn't match, but pre-configuring them is recommended for production.

When a user clicks "Upgrade," the client calls `POST /payment/create-subscription`. This creates a Razorpay subscription and returns the subscription ID. The Razorpay checkout widget loads in the browser, and after payment, the client sends `POST /payment/verify-subscription`. The server computes the expected HMAC-SHA256 signature using `razorpay_payment_id|razorpay_subscription_id` and the Key Secret, then compares it with the signature Razorpay returned. If it matches, the user's `is_premium` flag is set to `True` and a premium welcome email is sent.

The webhook endpoint (`POST /payment/webhook`) handles five events: `subscription.activated` (sets premium flag), `subscription.charged` (records payment in `subscription_payments`, extends expiry), `subscription.cancelled` (flags cancel requested), `subscription.completed` (same as cancelled), and `payment.failed` (sends payment failure email). Webhook signatures are verified using HMAC-SHA256 with the raw request body and `RAZORPAY_WEBHOOK_SECRET` before any processing occurs.

### Session Booking Flow

Session bookings use Razorpay Orders (single payments, not subscriptions). The client calls `POST /shadow-sessions/book/<id>/create-order`, which creates a Razorpay order and inserts a `pending` `SessionBooking` record. After payment, `POST /shadow-sessions/book/<id>/verify-payment` uses `razorpay.utility.verify_payment_signature` to validate the signature. On success, the booking status moves to `paid` and confirmation emails go to both the booker and provider.

### Testing

Use Razorpay test credentials (Key ID starting with `rzp_test_`). Test card numbers are available in the Razorpay documentation. No real charges occur in test mode.

---

## AI Integration

PathMap uses **Google Gemini 2.5 Flash** via the `google-genai` SDK for seven distinct AI-powered features.

All calls go through `app/services/ai_service.py`. The shared client is initialised at module level: `client = genai.Client()`. The API key is read from the environment by the SDK automatically when `GEMINI_API_KEY` is set. Every function wraps the API call in a `try/except` and returns a sensible fallback string on any failure, so AI unavailability degrades gracefully rather than breaking core flows.

**`get_dashboard_welcome(user, assessment)`** — generates a 60–80 word personalised welcome message shown on the dashboard each day. It is cached in the Flask session keyed by date, so the API is called at most once per user per day.

**`get_ai_career_insight(question, context)`** — answers a freeform career question using the user's profile context (current role, years of experience, pivot motivation, whether assessment is complete, top values). Free users get 3 questions per day (tracked in session); Premium users have no limit.

**`get_job_market_insights(role_title)`** — fetches a current job market overview for a target role in India using Gemini's `GoogleSearch` grounding tool. This is the only function that uses real-time web data. Called on demand from the analysis detail page.

**`generate_career_profile_narrative(profile_summary)`** — creates a 200–250 word second-person career narrative from the completed assessment. Called once at assessment completion; stored in `profile_summary.ai_narrative`.

**`generate_decision_commitment_statement(decision_data)`** — generates a 3-5 sentence commitment statement at Step 5 of the Decision Confidence Framework, referencing the chosen direction, values, and key assumption.

**`enrich_roadmap_tasks_with_ai(milestones, role, gap_skills)`** — via `generate_roadmap_task_descriptions`, writes a 70–90 word task description for each of the top 3 most important skill tasks in the generated roadmap.

**`generate_reflection_insight(reflection, week, mood)`** — responds to a user's weekly check-in reflection with a 2-3 sentence insight acknowledging their situation and suggesting one concrete next step.

---

## Security Architecture

**Password Hashing**: All passwords are hashed using `pbkdf2:sha256` with a 16-byte salt via `werkzeug.security.generate_password_hash`. Plaintext passwords are never stored.

**CSRF Protection**: Flask-WTF (`CSRFProtect`) adds CSRF tokens to all HTML forms and validates them on POST. The Razorpay webhook route is explicitly exempted with `@csrf.exempt` because it's a server-to-server call with its own signature-based authentication. In production, `WTF_CSRF_SSL_STRICT=True` is enforced.

**Session Security**: Sessions use `SESSION_COOKIE_HTTPONLY=True` (JavaScript cannot read the cookie) and `SESSION_COOKIE_SAMESITE=Lax` (prevents cross-site request forgery in most cases). In production, `SESSION_COOKIE_SECURE=True` ensures cookies are only sent over HTTPS.

**Email Verification Tokens**: Generated with `itsdangerous.URLSafeTimedSerializer` and expire after 24 hours. The token encodes the user ID and a `purpose` field (`verify`) to prevent token reuse across flows.

**Password Reset Tokens**: Also via `URLSafeTimedSerializer`, expiring after 1 hour. A hash fragment of the current password hash is included in the token payload, so the token is automatically invalidated if the password is changed or reset while the token is still live.

**Rate Limiting**: Flask-Limiter applies IP-based rate limits: 5 sign-ups per hour, 10 login attempts per 15 minutes, 3 password reset requests per hour.

**Payment Signature Verification**: All Razorpay signatures are verified with HMAC-SHA256 before any database state changes occur. Subscription payments use `payment_id|subscription_id` as the message body; webhook events use the raw request body. `hmac.compare_digest` is used for constant-time comparison to prevent timing attacks.

**Data Ownership Enforcement**: Every owner-restricted route checks `if analysis.user_id != current_user.id: abort(403)` before returning or modifying data. This pattern is consistent across analyses, roadmaps, bookings, decision summaries, and all similar resources.

**Input Sanitisation**: User-generated content in journey narratives and assessment responses is stored as plaintext. When blog or admin content is rendered as Markdown, it passes through `bleach.clean()` with an allowed-tags whitelist before reaching the browser. Trusted admin content can bypass sanitisation via `markdown_trusted` filter for internal rendering.

**SQL Injection Prevention**: All database access goes through SQLAlchemy's ORM with parameterised queries. No raw SQL strings with string interpolation are used.

**Forgot Password Email Enumeration**: The forgot-password endpoint always returns the same flash message regardless of whether the email exists in the database, preventing user enumeration through differential responses.

**GDPR Deletion**: When executed by an admin, the deletion process anonymises the user record (email replaced with `deleted_{id}@pathmap.deleted`, name replaced with `Deleted User`, password hash set to `DELETED`) and either deletes or anonymises all associated data. Session bookings are anonymised (not deleted) to preserve financial records.

---

## Admin Panel

Access the admin panel at `/admin/` with a user account that has `is_admin=True`.

After seeding, the default admin credentials are:
- Email: `admin@pathmap.in`
- Password: `Admin@PathMap2026!`

**Dashboard** shows seven KPI cards (total users, premium users, 90-day active users, pending GDPR, 30-day revenue, published/unpublished journeys) plus a revenue trend chart, booking trend chart, top 5 journeys by views, and pending action counts.

**Users** (`/admin/users`) lists the most recent 200 users with action buttons to toggle active/inactive status, toggle admin flag, and grant permanent premium access. All actions require CSRF token validation and are logged to the audit log.

**Journeys** (`/admin/journeys`) shows all submissions ordered by submit date. Admins can publish, unpublish, or reject with a written reason. The rejection reason is stored and visible to the submitter.

**Providers** (`/admin/providers`) shows active provider profiles and pending applications. Approving an application creates a verified `ShadowSessionProvider` record and sets the user's `is_journey_provider=True`. Rejection records a reason on the application.

**Sessions** (`/admin/sessions`) shows all bookings ordered by date with a manual "Mark Refunded" action.

**Blog** (`/admin/blog`) is a simple CMS: fill in title, slug, content (Markdown supported), excerpt, tags, and published flag. Slugs are unique-enforced.

**GDPR** (`/admin/gdpr`) lists users who have requested data deletion. Admins execute each deletion, which triggers the full anonymisation workflow and a confirmation email to the user.

**Revenue Export** (`/admin/revenue/export`) generates a timestamped CSV of all subscription payments.

**Audit Log** (`/admin/audit-log`) shows the last 200 admin actions with timestamp, admin identity, action type, target, and IP address.

Admin access is enforced by the `@admin_required` decorator, which returns 403 for any non-admin authenticated request.

---

## Testing

PathMap does not currently include automated tests. The codebase has a `TestingConfig` class configured with `WTF_CSRF_ENABLED=False` and an in-memory SQLite database, which is ready for use with pytest and Flask's test client.

If you want to add tests, the highest-value areas to start with are the skill transfer engine (`app/services/skill_engine.py`), the feasibility scorer (`app/services/feasibility.py`), the assessment computation functions (`app/services/assessment_proc.py`), and the payment signature verification logic in `app/routes/payment.py`. These are the most logic-dense, side-effect-free modules and will catch regressions quickly.

A recommended setup:

```bash
pip install pytest pytest-flask
```

```python
# tests/conftest.py
import pytest
from app import create_app

@pytest.fixture
def app():
    app = create_app('testing')
    yield app

@pytest.fixture
def client(app):
    return app.test_client()
```

---

## Deployment

### Environment Variables

Before deploying to production, change these from their development defaults:

```bash
FLASK_ENV=production
SECRET_KEY=<random 64-character string>
DATABASE_URL=postgresql://user:password@host:5432/pathmap
SESSION_COOKIE_SECURE=True        # Set automatically by ProductionConfig
BASE_URL=https://yourdomain.com
```

### Database Setup

Run migrations against the production database:

```bash
export FLASK_APP=run.py
flask db upgrade
flask seed-db
flask create-admin
```

### Running with Gunicorn

Gunicorn is included in `requirements.txt`. A basic production command:

```bash
gunicorn --workers 4 --bind 0.0.0.0:8000 "run:app"
```

For better performance with gevent workers:

```bash
pip install gevent
gunicorn --worker-class gevent --workers 4 --bind 0.0.0.0:8000 "run:app"
```

### Nginx Configuration

Serve static files directly from Nginx and proxy dynamic requests to Gunicorn:

```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;

    location /static/ {
        alias /path/to/pathmap/app/static/;
        expires 1y;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Razorpay Webhook

Register the production webhook URL in your Razorpay Dashboard under Settings → Webhooks:

```
https://yourdomain.com/payment/webhook
```

Enable these events: `subscription.activated`, `subscription.charged`, `subscription.cancelled`, `subscription.completed`, `payment.failed`.

### SSL

Use Certbot (Let's Encrypt) for free SSL certificates:

```bash
certbot --nginx -d yourdomain.com
```

---

## Seeded Data

Running `flask seed-db` populates the database with a full starter dataset. The seeder is idempotent — re-running it updates existing records without creating duplicates.

**Admin user**: `admin@pathmap.in` / `Admin@PathMap2026!` with `is_admin=True`, `is_premium=True`, `subscription_tier='admin_granted'`.

**Skills**: 97 professional skills across 14 categories (Communication, Analytical, Technical, Design, Leadership, Domain, Product, Data, Engineering, Growth, Operations, People, Sales, Finance).

**Roles**: 60+ career roles across Product, Growth, Finance, Technology, Creative & Design, Business & Strategy, Marketing, Data, and Operations categories. Each role includes a title, category, and description.

**Role-Skill Requirements**: Importance-weighted skill mappings for each role, defining which skills matter most for each career target.

**Learning Resources**: Curated learning resources per skill, covering providers like Coursera, Udemy, Codecademy, and others — with format, cost tier, estimated hours, and quality ratings.

**Career Journeys**: Sample published career pivot stories covering various origin-to-target transitions, including completed and in-progress outcomes with realistic details.

**Shadow Session Providers**: Sample verified session providers with bios, pricing, and ratings.

**Blog Posts**: Sample published articles on career pivot topics.

To verify seeding worked, check the console output after `flask seed-db` — it prints counts for each entity type. You can also log in as admin and confirm the Resources library shows content.

---

## Free vs Paid Features

| Feature | Free | Premium (₹1,499/month or ₹11,999/year) |
|---|---|---|
| Career Clarity Assessment (all 5 modules) | ✅ Unlimited | ✅ Unlimited |
| AI-generated career profile narrative | ✅ | ✅ |
| Skill Transfer Analysis | 1 per calendar month | ✅ Unlimited |
| Feasibility scoring | ✅ (included in analysis) | ✅ Included |
| Analysis comparison (up to 3) | ✅ | ✅ |
| Skill slider adjustments | ✅ | ✅ |
| What-if feasibility modelling | ✅ | ✅ |
| AI job market insights | ✅ (on any analysis) | ✅ |
| AI dashboard welcome message | ✅ (once per day) | ✅ |
| AI career insight questions | 3 per day | ✅ Unlimited |
| Decision Confidence Framework | ❌ | ✅ |
| Decision Summary PDF download | ❌ | ✅ |
| 90-Day Pivot Roadmap generation | ❌ | ✅ |
| AI-enriched roadmap task descriptions | ❌ | ✅ |
| Task completion tracking on roadmap | ❌ | ✅ |
| Weekly check-ins | ✅ (requires roadmap) | ✅ |
| AI reflection insights | ✅ | ✅ |
| Progress heatmap and streak | ✅ | ✅ |
| Progress history | ✅ | ✅ |
| Progress history CSV export | ❌ | ✅ |
| Career journey explorer | ✅ (5 stories/month) | ✅ Unlimited |
| Shadow session marketplace browsing | ✅ | ✅ |
| Shadow session booking | ❌ | ✅ |
| Resource library | ✅ (up to 2 per skill) | ✅ Full access |
| Resource bookmarks | ✅ (up to 5) | ✅ Unlimited |
| Personal data export (JSON) | ✅ | ✅ |

---

## Known Limitations and Future Improvements

**No automated test suite**: The `TestingConfig` class exists but no test files are present. This is the largest gap for a production deployment.

**Razorpay plan IDs require manual pre-configuration**: The auto-create-plan fallback in `_ensure_plan_id()` works, but configuring `RAZORPAY_MONTHLY_PLAN_ID` and `RAZORPAY_ANNUAL_PLAN_ID` explicitly in `.env` is the right production path. The comments in `payment.py` note this clearly.

**Rate limiting uses in-memory storage**: `RATELIMIT_STORAGE_URL = 'memory://'` in `BaseConfig` means rate limit counters are lost on server restart and not shared across multiple Gunicorn workers or instances. For production, change this to a Redis URL.

**AI calls have no retry logic**: Every Gemini call is wrapped in a bare `try/except` with a static fallback. Adding exponential backoff for transient failures would improve reliability under load.

**No background task queue**: All AI calls, PDF generation, and email sending happen synchronously in the request cycle. Long AI responses (market insights, profile narratives) will block the request. Moving these to Celery or RQ would improve perceived performance.

**Blog has no slug auto-uniqueness from admin UI**: The admin blog form auto-generates a slug from the title, but if a slug collision occurs, it flashes an error and requires manual correction. The helper `generate_slug()` exists in `utils/helpers.py` but isn't wired to the admin blog form.

**No pagination on admin user list**: Admin `GET /admin/users` returns the most recent 200 users with `.limit(200)`. This will become insufficient as the user base grows.

**Provider images**: The `ShadowSessionProvider` model has no profile photo field. The UI would benefit from provider avatars.

**Subscription renewal is webhook-driven only**: If a webhook event is missed (network error, Razorpay outage), the subscription expiry won't be extended on time. A daily cron job that reconciles Razorpay subscription status against local expiry dates would make the system more resilient.

---

## Contributing

PathMap welcomes contributions. Here's how to get started.

Fork the repository on GitHub and clone your fork:

```bash
git clone https://github.com/your-username/PathMap.git
cd PathMap
```

Create a feature branch. Use lowercase, hyphen-separated names that describe the change:

```bash
git checkout -b feature/add-resource-ratings
git checkout -b fix/roadmap-start-date-edge-case
git checkout -b refactor/skill-engine-adjacency
```

Make your changes, keeping functions small and testable. The codebase uses consistent patterns throughout — service modules contain business logic, routes stay thin, decorators handle auth. Follow the same conventions.

If you add a new route, add it to the Routes Reference in this README. If you add a new model field, note it in the Database Schema section. Keeping documentation in sync with code is just as important as the code itself.

Run through the affected user flows manually before opening a pull request. Because there are no automated tests yet, a brief note in your PR description about what you tested manually is appreciated.

Submit a pull request against the `main` branch with a clear title and description. Explain what problem you're solving, not just what you changed.

To report a bug or request a feature, open a GitHub Issue with as much context as you can provide — steps to reproduce for bugs, and the user problem being solved for features.

---

## License

No LICENSE file was found in this repository. Without a license, the code is technically "all rights reserved" by default, meaning others cannot use, copy, modify, or distribute it.

If you intend PathMap to be open-source, add a `LICENSE` file to the root of the repository. For a permissive open-source license, MIT is a common choice:

```
MIT License

Copyright (c) 2026 PathMap

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction...
```

You can generate the full MIT license text at [choosealicense.com/licenses/mit/](https://choosealicense.com/licenses/mit/).

---

## Acknowledgments

PathMap is built on a strong foundation of open-source libraries and commercial services:

- **Flask** and the broader Pallets Projects ecosystem (Werkzeug, Jinja2, Click) — the entire web framework stack
- **Flask-SQLAlchemy**, **Flask-Migrate**, **Flask-Login**, **Flask-WTF**, **Flask-Mail**, **Flask-Limiter** — Flask extension authors
- **Google Generative AI (Gemini)** — AI features throughout the product
- **Razorpay** — payment infrastructure and excellent developer documentation
- **ReportLab** — PDF generation
- **Python-Markdown**, **bleach**, and **Pygments** — content rendering pipeline
- **Bootstrap** (CDN) — responsive UI components
- **Bootstrap Icons** — icon set
- All contributors to the Python packaging ecosystem

---

## Contact and Support

For bug reports and feature requests, open an issue on the GitHub repository.

For questions about setting up or deploying PathMap, use the GitHub Discussions tab.

Support email visible in the codebase: **support@pathmap.in**

Admin contact: **admin@pathmap.in**

If you encounter a payment-related issue in production, contact Razorpay support directly with your order/subscription ID, and reach out via the support email with the same details.