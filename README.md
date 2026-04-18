# Personal Data Sovereignty Platform

A cross-platform-ready **Personal Data Sovereignty** application with:
- Responsive web app (mobile-friendly) served from one codebase.
- API-first backend suitable for native mobile clients using the same endpoints.
- SQLite persistence where all user-owned records include a `user_id` column.

## Core capabilities delivered

- **Landing page (no auth)** with trust + earnings messaging and sign-up/log-in CTA.
- **Authenticated dashboard** sections for Data Vault, Permissions, Monetization Marketplace, Privacy Layer, AI Insights, Notifications, Realtime presence, Billing, Settings, and Admin portal.
- **Data Vault** source connection + encrypted payload storage simulation + item search/filter.
- **Permissions** granular records and instant revoke endpoint.
- **Marketplace** listing creation, bidding/offers, Stripe webhook success simulation, wallet updates, and earnings history.
- **Privacy layer** differential privacy preview and sensitive-field redaction.
- **AI Insights** streaming endpoint (SSE) for realtime cards.
- **Notifications** records for new bids, sales, and permission changes.
- **Plans & Billing** free/pro logic and coupon (`TESTCOUPON`) test flow.
- **Settings** payment methods, GDPR/CCPA request center, account deletion.
- **Admin portal** dispute/compliance case management.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn pydantic[email]
uvicorn main:app --reload
```

Then open `http://127.0.0.1:8000`.

## API overview

- Auth: `/api/auth/signup`, `/api/auth/login`
- Data vault: `/api/vault/sources`, `/api/vault/items`
- Permissions: `/api/permissions`, `/api/permissions/{id}/revoke`
- Marketplace: `/api/marketplace/listings`, `/api/marketplace/offers`, `/api/stripe/webhook/success`
- Privacy: `/api/privacy/preview`, `/api/privacy/redact`
- Insights stream: `/api/insights/stream`
- Notifications: `/api/notifications`
- Realtime presence: `/api/realtime/presence`
- Billing: `/api/billing/subscription`
- Settings: `/api/settings/payment-methods`, `/api/settings/gdpr-request`, `/api/settings/account`
- Admin: `/api/admin/cases`

## Tech notes

- Persistence: SQLite (`data/pds_platform.db`).
- UI: static HTML/CSS/JS in `templates/pds/`.
- Backend: FastAPI + Pydantic models in `main.py`.

