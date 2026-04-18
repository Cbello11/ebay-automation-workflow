"""Personal Data Sovereignty platform API + landing page server.

Run with:
    uvicorn main:app --reload
"""

from __future__ import annotations

import base64
import hashlib
import random
import secrets
from datetime import datetime
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr

from src.core.platform_db import (
    execute,
    fetch_all,
    fetch_one,
    init_db,
    insert_row,
    now_ts,
    to_json,
)

app = FastAPI(title="Personal Data Sovereignty API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/assets", StaticFiles(directory="templates/pds"), name="assets")


class SignupRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(SignupRequest):
    pass


class DataSourceRequest(BaseModel):
    user_id: str
    category: str
    source_name: str
    metadata: dict = {}


class DataItemRequest(BaseModel):
    user_id: str
    category: str
    source_name: str
    raw_data: dict


class PermissionRequest(BaseModel):
    user_id: str
    company_name: str
    dataset: str
    date_range: str
    purpose: str
    active: bool = True


class ListingRequest(BaseModel):
    user_id: str
    title: str
    anonymized_summary: str
    dataset_type: str
    pricing_mode: Literal["fixed", "bids"]
    fixed_price: float | None = None


class OfferRequest(BaseModel):
    user_id: str
    listing_id: int
    buyer_id: str
    amount: float


class SubscriptionRequest(BaseModel):
    user_id: str
    target_tier: Literal["free", "pro"]
    coupon_code: str | None = None


class GdprRequest(BaseModel):
    user_id: str
    request_type: Literal["export", "delete", "access"]


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def encrypt_client_side_placeholder(raw_data: dict) -> str:
    """Placeholder to model already encrypted client payload."""
    serialized = to_json(raw_data).encode("utf-8")
    return base64.b64encode(serialized).decode("utf-8")


def tier_fee(tier: str) -> float:
    return 0.0 if tier == "pro" else 0.05


@app.on_event("startup")
def setup() -> None:
    init_db()


@app.get("/", response_class=HTMLResponse)
def landing_page() -> str:
    return Path("templates/pds/index.html").read_text(encoding="utf-8")


@app.post("/api/auth/signup")
def signup(payload: SignupRequest):
    if fetch_one("SELECT user_id FROM users WHERE email = ?", (payload.email,)):
        raise HTTPException(400, "Email already exists")
    user_id = f"usr_{secrets.token_hex(8)}"
    insert_row(
        "users",
        {
            "user_id": user_id,
            "email": payload.email,
            "password_hash": hash_password(payload.password),
            "created_at": now_ts(),
        },
    )
    return {"user_id": user_id, "token": f"dev-token-{user_id}"}


@app.post("/api/auth/login")
def login(payload: LoginRequest):
    user = fetch_one(
        "SELECT user_id, password_hash, tier, wallet_balance FROM users WHERE email = ?",
        (payload.email,),
    )
    if not user or user["password_hash"] != hash_password(payload.password):
        raise HTTPException(401, "Invalid credentials")
    return {
        "user_id": user["user_id"],
        "tier": user["tier"],
        "wallet_balance": user["wallet_balance"],
        "token": f"dev-token-{user['user_id']}",
    }


@app.post("/api/vault/sources")
def add_data_source(payload: DataSourceRequest):
    source_count = fetch_one(
        "SELECT COUNT(*) AS count FROM data_sources WHERE user_id = ?", (payload.user_id,)
    )["count"]
    user = fetch_one("SELECT tier FROM users WHERE user_id = ?", (payload.user_id,))
    if not user:
        raise HTTPException(404, "User not found")
    if user["tier"] == "free" and source_count >= 3:
        raise HTTPException(402, "Free tier allows only 3 sources. Upgrade to Pro.")

    source_id = insert_row(
        "data_sources",
        {
            "user_id": payload.user_id,
            "category": payload.category,
            "source_name": payload.source_name,
            "connected_at": now_ts(),
            "metadata": to_json(payload.metadata),
        },
    )
    return {"source_id": source_id}


@app.get("/api/vault/items")
def list_data_items(user_id: str, category: str | None = None, search: str | None = None):
    query = "SELECT * FROM data_items WHERE user_id = ?"
    params: list = [user_id]
    if category:
        query += " AND category = ?"
        params.append(category)
    if search:
        query += " AND (category LIKE ? OR source_name LIKE ?)"
        token = f"%{search}%"
        params.extend([token, token])
    query += " ORDER BY created_at DESC"
    return fetch_all(query, tuple(params))


@app.post("/api/vault/items")
def add_data_item(payload: DataItemRequest):
    item_id = insert_row(
        "data_items",
        {
            "user_id": payload.user_id,
            "category": payload.category,
            "source_name": payload.source_name,
            "encrypted_payload": encrypt_client_side_placeholder(payload.raw_data),
            "created_at": now_ts(),
        },
    )
    return {"item_id": item_id, "encrypted": True}


@app.delete("/api/vault/items/{item_id}")
def delete_data_item(item_id: int, user_id: str):
    execute("DELETE FROM data_items WHERE id = ? AND user_id = ?", (item_id, user_id))
    return {"deleted": True}


@app.post("/api/permissions")
def create_permission(payload: PermissionRequest):
    permission_id = insert_row(
        "permissions",
        {
            "user_id": payload.user_id,
            "company_name": payload.company_name,
            "dataset": payload.dataset,
            "date_range": payload.date_range,
            "purpose": payload.purpose,
            "active": int(payload.active),
            "updated_at": now_ts(),
        },
    )
    return {"permission_id": permission_id}


@app.patch("/api/permissions/{permission_id}/revoke")
def revoke_permission(permission_id: int, user_id: str):
    execute(
        "UPDATE permissions SET active = 0, updated_at = ? WHERE id = ? AND user_id = ?",
        (now_ts(), permission_id, user_id),
    )
    insert_row(
        "notifications",
        {
            "user_id": user_id,
            "event_type": "permissions",
            "message": "A permission was revoked instantly.",
            "created_at": now_ts(),
        },
    )
    return {"revoked": True}


@app.get("/api/permissions")
def list_permissions(user_id: str):
    return fetch_all("SELECT * FROM permissions WHERE user_id = ? ORDER BY updated_at DESC", (user_id,))


@app.post("/api/marketplace/listings")
def create_listing(payload: ListingRequest):
    listing_id = insert_row(
        "listings",
        {
            "user_id": payload.user_id,
            "title": payload.title,
            "anonymized_summary": payload.anonymized_summary,
            "dataset_type": payload.dataset_type,
            "pricing_mode": payload.pricing_mode,
            "fixed_price": payload.fixed_price,
            "created_at": now_ts(),
        },
    )
    return {"listing_id": listing_id}


@app.get("/api/marketplace/listings")
def browse_listings():
    return fetch_all("SELECT id, title, anonymized_summary, dataset_type, pricing_mode, fixed_price, status FROM listings WHERE status='active' ORDER BY created_at DESC")


@app.post("/api/marketplace/offers")
def make_offer(payload: OfferRequest):
    offer_id = insert_row(
        "offers",
        {
            "user_id": payload.user_id,
            "listing_id": payload.listing_id,
            "buyer_id": payload.buyer_id,
            "amount": payload.amount,
            "created_at": now_ts(),
        },
    )
    insert_row(
        "notifications",
        {
            "user_id": payload.user_id,
            "event_type": "new_bid",
            "message": f"New bid received: ${payload.amount:.2f}",
            "created_at": now_ts(),
        },
    )
    return {"offer_id": offer_id, "checkout_url": f"/stripe/checkout/mock/{offer_id}"}


@app.post("/api/stripe/webhook/success")
def stripe_webhook_success(offer_id: int):
    offer = fetch_one("SELECT * FROM offers WHERE id = ?", (offer_id,))
    if not offer:
        raise HTTPException(404, "Offer not found")
    listing = fetch_one("SELECT * FROM listings WHERE id = ?", (offer["listing_id"],))
    user = fetch_one("SELECT tier, wallet_balance FROM users WHERE user_id = ?", (offer["user_id"],))
    if not listing or not user:
        raise HTTPException(404, "Listing or seller not found")

    fee_percent = tier_fee(user["tier"])
    net_amount = float(offer["amount"]) * (1 - fee_percent)
    execute(
        "UPDATE users SET wallet_balance = wallet_balance + ? WHERE user_id = ?",
        (net_amount, offer["user_id"]),
    )
    execute("UPDATE offers SET status='paid' WHERE id = ?", (offer_id,))
    insert_row(
        "earnings_history",
        {
            "user_id": offer["user_id"],
            "listing_id": listing["id"],
            "amount": offer["amount"],
            "fee_percent": fee_percent,
            "net_amount": net_amount,
            "stripe_session_id": f"mock_session_{offer_id}",
            "created_at": now_ts(),
        },
    )
    insert_row(
        "notifications",
        {
            "user_id": offer["user_id"],
            "event_type": "sale_complete",
            "message": "Sale completed and wallet updated.",
            "created_at": now_ts(),
        },
    )
    return {"delivered_dataset": listing["anonymized_summary"], "wallet_updated": True}


@app.get("/api/earnings")
def earnings(user_id: str):
    history = fetch_all(
        "SELECT * FROM earnings_history WHERE user_id = ? ORDER BY created_at DESC", (user_id,)
    )
    total = sum(row["net_amount"] for row in history)
    return {"total_net": total, "history": history}


@app.post("/api/privacy/preview")
def differential_privacy_preview(user_id: str, epsilon: float, value: float):
    noise = random.uniform(-1, 1) * (1 / max(epsilon, 0.01))
    return {
        "user_id": user_id,
        "original": value,
        "epsilon": epsilon,
        "noise": round(noise, 4),
        "private_value": round(value + noise, 4),
    }


@app.post("/api/privacy/redact")
def redact(payload: dict):
    sensitive = {"email", "ssn", "phone", "address", "name"}
    return {k: ("[REDACTED]" if k.lower() in sensitive else v) for k, v in payload.items()}


@app.get("/api/insights/stream")
def insights_stream(user_id: str):
    cards = [
        "Spending increased 12% week-over-week.",
        "Sleep quality positively correlates with productivity on Tue/Thu.",
        "High-value anonymized health trend bundle likely to attract bids.",
        "Anomaly: unusual location access from a new app.",
    ]

    def event_gen():
        for message in cards:
            yield f"data: {message}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@app.get("/api/notifications")
def list_notifications(user_id: str):
    return fetch_all(
        "SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC", (user_id,)
    )


@app.get("/api/realtime/presence")
def presence(listing_id: int):
    return {"listing_id": listing_id, "buyers_live": random.randint(0, 7)}


@app.post("/api/billing/subscription")
def update_subscription(payload: SubscriptionRequest):
    if payload.target_tier == "pro":
        price = 19.0
        discount = 5.0 if payload.coupon_code == "TESTCOUPON" else 0.0
        checkout_total = price - discount
    else:
        checkout_total = 0.0
    execute("UPDATE users SET tier = ? WHERE user_id = ?", (payload.target_tier, payload.user_id))
    return {"tier": payload.target_tier, "checkout_total": checkout_total}


@app.post("/api/settings/payment-methods")
def add_payment_method(user_id: str, provider: str, reference: str):
    method_id = insert_row(
        "payment_methods",
        {
            "user_id": user_id,
            "provider": provider,
            "reference": reference,
            "created_at": now_ts(),
        },
    )
    return {"method_id": method_id}


@app.post("/api/settings/gdpr-request")
def create_gdpr_request(payload: GdprRequest):
    request_id = insert_row(
        "gdpr_requests",
        {
            "user_id": payload.user_id,
            "request_type": payload.request_type,
            "status": "queued",
            "created_at": now_ts(),
        },
    )
    return {"request_id": request_id, "status": "queued"}


@app.delete("/api/settings/account")
def delete_account(user_id: str):
    for table in [
        "data_sources",
        "data_items",
        "permissions",
        "listings",
        "offers",
        "earnings_history",
        "notifications",
        "payment_methods",
        "gdpr_requests",
        "admin_cases",
    ]:
        execute(f"DELETE FROM {table} WHERE user_id = ?", (user_id,))
    execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    return {"deleted": True, "user_id": user_id}


@app.get("/api/admin/cases")
def admin_cases(status: str | None = None):
    if status:
        return fetch_all("SELECT * FROM admin_cases WHERE status = ? ORDER BY created_at DESC", (status,))
    return fetch_all("SELECT * FROM admin_cases ORDER BY created_at DESC")


@app.post("/api/admin/cases")
def create_admin_case(user_id: str, case_type: str, notes: str):
    case_id = insert_row(
        "admin_cases",
        {
            "user_id": user_id,
            "case_type": case_type,
            "notes": notes,
            "status": "open",
            "created_at": now_ts(),
        },
    )
    return {"case_id": case_id}
