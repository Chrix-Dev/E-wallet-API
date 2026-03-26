# Aza Pay — Wallet API

A production-ready digital wallet backend API built with FastAPI and PostgreSQL. Supports user authentication, wallet management, peer-to-peer transfers, Paystack-powered funding and withdrawals, transaction history, PDF statement export, and a tiered KYC system.

Built as a portfolio project targeting Nigerian fintech engineering roles.

---

## Live API

**Base URL:** `https://aza-pay-api.onrender.com/`  
**Swagger Docs:** `https://aza-pay-api.onrender.com/docs`

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Framework | FastAPI | Async support handles concurrent I/O efficiently — critical for a payment system making DB, Redis, and external API calls simultaneously |
| Database | PostgreSQL (Supabase) | Relational data model fits financial data naturally. ACID transactions guarantee atomic money movement |
| ORM | SQLAlchemy + Alembic | Parameterized queries prevent SQL injection. Alembic provides versioned schema migrations |
| Cache / Rate limiting | Redis (Redis Cloud) | In-memory store for sub-millisecond reads. Used for balance caching and per-user rate limiting |
| Auth | JWT + Google OAuth2 | Short-lived access tokens (30min) + long-lived refresh tokens (7 days). Refresh tokens stored as SHA256 hashes — never raw |
| Payments | Paystack | Licensed Nigerian payment gateway. Handles card processing and bank transfers. We never touch sensitive payment data directly |
| Email | SendGrid | Transactional email for verification and notifications. Built for reliable delivery at scale unlike Gmail SMTP |
| PDF Export | ReportLab | Generates bank-style transaction statements |

---

## Key Engineering Decisions

**Money is never stored as float**  
All balance and amount columns use `Numeric(20, 2)` — PostgreSQL's exact decimal type. Floats have binary rounding errors (`0.1 + 0.2 = 0.30000000000000004`) which are unacceptable in financial systems.

**Atomic transfers**  
Wallet-to-wallet transfers debit the sender, credit the receiver, and create a transaction record in a single `db.commit()`. If anything fails the entire operation rolls back — no money disappears into an inconsistent state.

**Idempotency on mutations**  
Transfer and withdrawal endpoints require an `Idempotency-Key` header. Duplicate requests return the saved response without reprocessing. This prevents double charges from network retries.

**Webhook signature verification**  
Every Paystack webhook is verified via HMAC-SHA512 before processing. We recompute the hash using our secret key and compare with `hmac.compare_digest` (timing-safe comparison) to prevent spoofed webhook attacks.

**Debit-first withdrawals**  
Wallets are debited before calling Paystack. This prevents users from initiating multiple withdrawals before any settle. If the Paystack call fails, the debit is automatically reversed.

**Refresh tokens stored as hashes**  
Refresh tokens are stored as SHA256 hashes in the database. If the database is breached, raw tokens can't be used. Revocation on logout is enforced by marking the hash as revoked.

**Redis pipeline for rate limiting**  
`INCR` and `EXPIRE` are sent in a single Redis pipeline — one round trip instead of two. Small but correct.

**Lazy daily limit reset**  
Daily transfer and withdrawal limits reset by checking `last_daily_reset` on every transaction rather than running a scheduled job. Simpler, no cron dependency.

---

## Features

### Authentication
- Register with email and password
- Login with email and password
- Google OAuth2 login
- JWT access tokens (30 min) + refresh tokens (7 days)
- Email verification on registration via SendGrid
- Logout with token revocation
- Change password

### Wallet
- Wallet auto-created on registration with unique 10-digit account number
- Fund wallet via Paystack (real payment link)
- Wallet-to-wallet transfer (by email or account number)
- Withdrawal to any Nigerian bank account via Paystack
- Transaction PIN required for transfers and withdrawals
- Wallet locks after 3 wrong PIN attempts

### KYC Tier System
Modeled on CBN tiered KYC requirements:

| Tier | Requirements | Transfer Limit | Daily Limit |
|---|---|---|---|
| Tier 1 | Email verified | ₦100,000 | ₦200,000 |
| Tier 2 | BVN + phone + DOB | ₦500,000 | ₦1,000,000 |
| Tier 3 | ID document + address | ₦2,000,000 | ₦5,000,000 |

### Transactions
- Full transaction history with filters (type, status, date range)
- Pagination
- Single transaction lookup by reference
- PDF statement export (bank-statement style)

### Notifications (SendGrid)
- Email verification on signup
- Wallet funded
- Transfer sent
- Transfer received
- Withdrawal successful
- Withdrawal failed + balance reversed

### Admin Dashboard
- Overview stats (total users, transaction volume, success rate)
- List and filter all users
- View user details + wallet
- Activate/deactivate user accounts
- List and filter all transactions
- Unlock user PIN after lockout
- Admin accounts created via secure DB script — no public registration endpoint

---

## API Endpoints

```
AUTH
  POST   /api/v1/auth/register
  POST   /api/v1/auth/login
  POST   /api/v1/auth/refresh
  POST   /api/v1/auth/logout
  GET    /api/v1/auth/google
  GET    /api/v1/auth/google/callback
  GET    /api/v1/auth/me
  GET    /api/v1/auth/verify
  POST   /api/v1/auth/change-password

WALLETS
  GET    /api/v1/wallets/me
  POST   /api/v1/wallets/fund
  POST   /api/v1/wallets/transfer
  POST   /api/v1/wallets/withdraw
  POST   /api/v1/wallets/set-pin
  POST   /api/v1/wallets/change-pin

TRANSACTIONS
  GET    /api/v1/transactions
  GET    /api/v1/transactions/{reference}
  GET    /api/v1/transactions/export/pdf

USERS
  POST   /api/v1/users/upgrade-tier2
  POST   /api/v1/users/upgrade-premium
  GET    /api/v1/users/me/limits

ADMIN
  GET    /api/v1/admin/dashboard
  GET    /api/v1/admin/users
  GET    /api/v1/admin/users/{user_id}
  PATCH  /api/v1/admin/users/{user_id}/toggle
  PATCH  /api/v1/admin/users/{user_id}/unlock-pin
  GET    /api/v1/admin/transactions
  GET    /api/v1/admin/transactions/{reference}

WEBHOOKS
  POST   /api/v1/webhooks/paystack
```

---

## Running Locally

### Prerequisites
- Python 3.10+
- PostgreSQL (or Supabase account)
- Redis (or Redis Cloud account)
- Paystack test account
- SendGrid account

### Setup

```bash
# clone the repo
git clone https://github.com/Chrix-Dev/Aza-pay-API.git
cd Aza-pay-API

# create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# install dependencies
pip install -r requirements.txt

# create .env file
cp .env.example .env
# fill in your credentials
```

### Environment Variables

```env
APP_NAME="Aza Pay API"
DEBUG=True
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

DATABASE_URL=postgresql+asyncpg://...
SYNC_DATABASE_URL=postgresql+psycopg2://...

REDIS_URL=redis://...

GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback

PAYSTACK_SECRET_KEY=sk_test_...

SENDGRID_API_KEY=SG....
SENDGRID_SENDER_EMAIL=your@email.com

ADMIN_EMAIL=admin@azapay.com
ADMIN_PASSWORD=your-admin-password
ADMIN_FULL_NAME=Super Admin
```

### Run migrations

```bash
alembic upgrade head
```

### Create admin user

```bash
python app/scripts/create_admin.py
```

### Start server

```bash
python -m uvicorn app.main:app --reload
```

Visit `http://localhost:8000/docs` for Swagger UI.

---

## Database Schema

```
users               — auth, profile, KYC tier, credentials
wallets             — balance, account number, daily limits, PIN
transactions        — all money movements with full audit trail
refresh_tokens      — hashed tokens with revocation support
idempotency_keys    — duplicate request prevention
verification_tokens — email verification flow
```

---

## What I'd Add in Production

- **Real BVN verification** via Smile ID or Paystack Identity (currently simulated)
- **Celery + Redis** for webhook processing queue instead of FastAPI BackgroundTasks
- **Read replicas** for transaction history queries
- **Sentry** for error monitoring and alerting
- **Test suite** covering critical financial paths
- **Rate limiting** at the infrastructure level (nginx/Cloudflare) in addition to application level

---

## Author

Built by [Christian](https://github.com/Chrix-Dev)