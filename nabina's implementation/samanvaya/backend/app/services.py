from __future__ import annotations

import csv
import io
import json
import random
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
from faker import Faker
from rapidfuzz import fuzz

from .database import connection

PROVIDERS = [
    "Bir Hospital",
    "Patan Hospital",
    "BPKIHS",
    "Koshi Hospital",
    "Dhulikhel Hospital",
]
PROVIDER_VARIANTS = {
    "Bir Hospital": ["BIR HOSPITAL", "Bir Hosp.", "Bir Hospital, Kathmandu"],
    "Patan Hospital": ["PATAN HOSPITAL", "Patan Hosp.", "Patan Hospital Pvt Ltd"],
    "BPKIHS": ["B.P. Koirala Institute of Health Sciences", "BPKIHS Dharan", "BPKIHS"],
    "Koshi Hospital": ["Koshi Hosp.", "KOSHI HOSPITAL", "Koshi Regional Hospital"],
    "Dhulikhel Hospital": ["Dhulikhel Hosp.", "DHULIKHEL HOSPITAL", "Dhulikhel Hospital Pvt. Ltd."],
}
DISTRICTS = ["Kathmandu", "Lalitpur", "Bhaktapur", "Morang", "Dhankuta", "Kavrepalanchok", "Sunsari"]
CATEGORY_COLORS = {
    "fully_matched": "#16a34a",
    "partial_match": "#eab308",
    "failed": "#dc2626",
    "anomaly": "#dc2626",
}

fake = Faker("en_US")
Faker.seed(42)
random.seed(42)


def normalize_provider(value: str) -> str:
    filtered = "".join(character.lower() if character.isalnum() else " " for character in value)
    return " ".join(filtered.split())


def provider_variant(provider: str) -> str:
    variants = PROVIDER_VARIANTS.get(provider, [])
    if variants and random.random() < 0.7:
        return random.choice(variants)
    return provider


def parse_amount(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = str(value).replace(",", "").replace("NPR", "").strip()
    return float(cleaned)


def parse_date(value: Any, fallback: date | None = None) -> str:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str) and value.strip():
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
        except ValueError:
            try:
                return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
            except ValueError:
                pass
    return (fallback or date.today()).isoformat()


def generate_synthetic_dataset(total_records: int = 500) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    claim_rows: list[dict[str, Any]] = []
    payment_rows: list[dict[str, Any]] = []
    categories = (
        ["exact"] * int(total_records * 0.65)
        + ["fuzzy"] * int(total_records * 0.20)
        + ["missing"] * int(total_records * 0.10)
        + ["anomaly"] * (total_records - int(total_records * 0.65) - int(total_records * 0.20) - int(total_records * 0.10))
    )
    random.shuffle(categories)
    today = date.today()

    for index in range(total_records):
        claim_id = f"CLM{index + 1:03d}"
        provider = random.choice(PROVIDERS)
        claim_amount = random.randint(18_000, 220_000)
        claim_date = today - timedelta(days=random.randint(1, 180))
        district = random.choice(DISTRICTS)
        category = categories[index]

        claim_record = {
            "claim_id": claim_id,
            "provider": provider,
            "claim_amount": round(float(claim_amount), 2),
            "claim_date": claim_date.isoformat(),
            "district": district,
            "member_id": f"MEM{index + 7000:05d}",
            "diagnosis": random.choice(["Delivery", "Surgery", "Inpatient", "Emergency", "Consultation"]),
            "raw": {"claim_id": claim_id, "provider": provider, "amount": claim_amount, "date": claim_date.isoformat()},
        }
        claim_rows.append(claim_record)

        if category == "missing":
            continue

        payment_ref = f"PAY{index + 1:04d}"
        payment_amount = claim_amount
        payment_provider = provider
        payment_date = claim_date + timedelta(days=random.randint(0, 5))

        if category == "fuzzy":
            payment_provider = provider_variant(provider)
            payment_amount = round(claim_amount * random.uniform(0.96, 1.04), 2)
            payment_date = claim_date + timedelta(days=random.randint(-3, 7))
        elif category == "anomaly":
            payment_amount = round(claim_amount * random.uniform(1.35, 1.95), 2)
            payment_provider = provider_variant(provider)
            payment_date = claim_date + timedelta(days=random.randint(2, 10))

        payment_rows.append(
            {
                "payment_ref": payment_ref,
                "claim_id": claim_id,
                "provider": payment_provider,
                "paid_amount": payment_amount,
                "payment_date": payment_date.isoformat(),
                "source": "SOSYS",
                "raw": {
                    "payment_ref": payment_ref,
                    "claim_id": claim_id,
                    "provider": payment_provider,
                    "paid_amount": payment_amount,
                    "payment_date": payment_date.isoformat(),
                },
            }
        )

        if category == "anomaly":
            payment_rows.append(
                {
                    "payment_ref": f"PAYDUP{index + 1:04d}",
                    "claim_id": claim_id,
                    "provider": payment_provider,
                    "paid_amount": payment_amount,
                    "payment_date": (payment_date + timedelta(days=1)).isoformat(),
                    "source": "SOSYS",
                    "raw": {
                        "payment_ref": f"PAYDUP{index + 1:04d}",
                        "claim_id": claim_id,
                        "provider": payment_provider,
                        "paid_amount": payment_amount,
                        "payment_date": (payment_date + timedelta(days=1)).isoformat(),
                    },
                }
            )

    ghost_payment_count = 5
    for index in range(ghost_payment_count):
        payment_rows.append(
            {
                "payment_ref": f"GHOST{index + 1:03d}",
                "claim_id": f"GHOST-CLM-{index + 1:03d}",
                "provider": random.choice(PROVIDERS),
                "paid_amount": round(random.randint(8_000, 40_000) * 1.0, 2),
                "payment_date": (today - timedelta(days=random.randint(2, 45))).isoformat(),
                "source": "SOSYS",
                "raw": {
                    "payment_ref": f"GHOST{index + 1:03d}",
                    "claim_id": f"GHOST-CLM-{index + 1:03d}",
                    "provider": random.choice(PROVIDERS),
                    "paid_amount": round(random.randint(8_000, 40_000) * 1.0, 2),
                    "payment_date": (today - timedelta(days=random.randint(2, 45))).isoformat(),
                },
            }
        )

    return claim_rows, payment_rows


def reset_and_seed_demo_data(total_records: int = 500) -> dict[str, int]:
    claims, payments = generate_synthetic_dataset(total_records)
    with connection() as conn:
        conn.execute("DELETE FROM reconciliations")
        conn.execute("DELETE FROM claims")
        conn.execute("DELETE FROM payments")
        conn.execute("DELETE FROM uploads")
        conn.execute("DELETE FROM audit_log")
        insert_claims(conn, claims)
        insert_payments(conn, payments)
        conn.execute(
            "INSERT INTO uploads (source_type, filename, record_count, status) VALUES (?, ?, ?, ?)",
            ("synthetic", "generated-seed", len(claims) + len(payments), "seeded"),
        )
    result = run_reconciliation()
    return {"claims": len(claims), "payments": len(payments), "reconciled": result["processed_claims"]}


def insert_claims(conn, claims: list[dict[str, Any]]) -> int:
    rows = []
    for claim in claims:
        rows.append(
            (
                claim["claim_id"],
                claim["provider"],
                float(claim["claim_amount"]),
                parse_date(claim["claim_date"]),
                claim.get("district", "Kathmandu"),
                json.dumps(claim, ensure_ascii=False),
            )
        )
    conn.executemany(
        """
        INSERT INTO claims (claim_id, provider, claim_amount, claim_date, district, raw_json)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(claim_id) DO UPDATE SET
            provider = excluded.provider,
            claim_amount = excluded.claim_amount,
            claim_date = excluded.claim_date,
            district = excluded.district,
            raw_json = excluded.raw_json
        """,
        rows,
    )
    return len(rows)


def insert_payments(conn, payments: list[dict[str, Any]]) -> int:
    rows = []
    for payment in payments:
        rows.append(
            (
                payment["payment_ref"],
                payment.get("claim_id"),
                payment["provider"],
                float(payment["paid_amount"]),
                parse_date(payment["payment_date"]),
                payment.get("source", "SOSYS"),
                json.dumps(payment, ensure_ascii=False),
            )
        )
    conn.executemany(
        """
        INSERT INTO payments (payment_ref, claim_id, provider, paid_amount, payment_date, source, raw_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(payment_ref) DO UPDATE SET
            claim_id = excluded.claim_id,
            provider = excluded.provider,
            paid_amount = excluded.paid_amount,
            payment_date = excluded.payment_date,
            source = excluded.source,
            raw_json = excluded.raw_json
        """,
        rows,
    )
    return len(rows)


def parse_openimis_bundle(raw_text: str, filename: str) -> tuple[list[dict[str, Any]], int]:
    payload = json.loads(raw_text)
    if isinstance(payload, dict) and payload.get("resourceType") == "Bundle":
        entries = payload.get("entry", [])
        claims = [normalize_openimis_claim(entry.get("resource", {})) for entry in entries]
    elif isinstance(payload, list):
        claims = [normalize_openimis_claim(item) for item in payload]
    elif isinstance(payload, dict):
        claims = [normalize_openimis_claim(payload)]
    else:
        raise ValueError("Unsupported OpenIMIS JSON structure")
    claims = [claim for claim in claims if claim.get("claim_id")]
    return claims, len(claims)


def normalize_openimis_claim(resource: dict[str, Any]) -> dict[str, Any]:
    claim_id = resource.get("claim_id") or resource.get("code") or resource.get("id")
    provider = (
        resource.get("provider")
        or resource.get("hospital_name")
        or resource.get("healthFacility", {}).get("name")
        or resource.get("providerName")
        or "Unknown Provider"
    )
    amount_value = (
        resource.get("amount")
        or resource.get("claimed")
        or resource.get("total", {}).get("value")
        or resource.get("claim_amount")
        or 0
    )
    claim_date = resource.get("date") or resource.get("created") or resource.get("dateClaimed") or date.today().isoformat()
    district = resource.get("district") or random.choice(DISTRICTS)
    return {
        "claim_id": str(claim_id),
        "provider": str(provider),
        "claim_amount": parse_amount(amount_value),
        "claim_date": parse_date(claim_date),
        "district": district,
        "raw": resource,
    }


def parse_sosys_payload(raw_text: str) -> tuple[list[dict[str, Any]], int]:
    if raw_text.lstrip().startswith("[") or raw_text.lstrip().startswith("{"):
        payload = json.loads(raw_text)
        if isinstance(payload, dict) and "payments" in payload:
            rows = payload["payments"]
        elif isinstance(payload, list):
            rows = payload
        elif isinstance(payload, dict):
            rows = [payload]
        else:
            rows = []
        payments = [normalize_sosys_payment(item) for item in rows]
        payments = [payment for payment in payments if payment.get("payment_ref")]
        return payments, len(payments)

    reader = csv.DictReader(io.StringIO(raw_text))
    payments = [normalize_sosys_payment(row) for row in reader]
    payments = [payment for payment in payments if payment.get("payment_ref")]
    return payments, len(payments)


def normalize_sosys_payment(row: dict[str, Any]) -> dict[str, Any]:
    provider = row.get("provider") or row.get("hospital_name") or row.get("hospital") or row.get("name") or "Unknown Provider"
    payment_ref = row.get("payment_ref") or row.get("transaction_id") or row.get("ref") or row.get("id")
    claim_id = row.get("claim_id") or row.get("claim_code") or row.get("code") or row.get("openimis_claim_id")
    paid_amount = row.get("paid_amount") or row.get("amount_paid") or row.get("amount") or row.get("paid") or 0
    payment_date = row.get("payment_date") or row.get("date") or row.get("created") or date.today().isoformat()
    return {
        "payment_ref": str(payment_ref),
        "claim_id": str(claim_id) if claim_id not in (None, "") else None,
        "provider": str(provider),
        "paid_amount": parse_amount(paid_amount),
        "payment_date": parse_date(payment_date),
        "source": row.get("source", "SOSYS"),
        "raw": row,
    }


def ingest_openimis(claims: list[dict[str, Any]], filename: str) -> dict[str, int]:
    with connection() as conn:
        inserted = insert_claims(conn, claims)
        conn.execute(
            "INSERT INTO uploads (source_type, filename, record_count, status) VALUES (?, ?, ?, ?)",
            ("openimis", filename, inserted, "uploaded"),
        )
    return {"records": inserted}


def ingest_sosys(payments: list[dict[str, Any]], filename: str) -> dict[str, int]:
    with connection() as conn:
        inserted = insert_payments(conn, payments)
        conn.execute(
            "INSERT INTO uploads (source_type, filename, record_count, status) VALUES (?, ?, ?, ?)",
            ("sosys", filename, inserted, "uploaded"),
        )
    return {"records": inserted}


def run_reconciliation() -> dict[str, Any]:
    with connection() as conn:
        claims = pd.read_sql_query("SELECT * FROM claims ORDER BY claim_date, claim_id", conn)
        payments = pd.read_sql_query("SELECT * FROM payments ORDER BY payment_date, payment_ref", conn)

        conn.execute("DELETE FROM reconciliations")

        if claims.empty:
            return {"processed_claims": 0, "fully_matched": 0, "partial_matches": 0, "failed": 0, "anomalies": 0}

        claims["normalized_provider"] = claims["provider"].fillna("").map(normalize_provider)
        payments["normalized_provider"] = payments["provider"].fillna("").map(normalize_provider)
        claims["claim_date"] = pd.to_datetime(claims["claim_date"])
        payments["payment_date"] = pd.to_datetime(payments["payment_date"])

        result_rows: list[dict[str, Any]] = []
        matched_payment_refs: set[str] = set()
        anomaly_counter = Counter()
        duplicate_payment_refs = set()

        payment_groups = payments.groupby("claim_id") if not payments.empty else defaultdict(list)
        for claim_id, group in payment_groups:
            if len(group) > 1:
                duplicate_payment_refs.update(group["payment_ref"].astype(str).tolist())

        for _, claim in claims.iterrows():
            claim_dict = claim.to_dict()
            claim_payment_candidates = payments[payments["claim_id"] == claim_dict["claim_id"]] if not payments.empty else pd.DataFrame()
            exact_candidates = claim_payment_candidates[
                (claim_payment_candidates["normalized_provider"] == claim_dict["normalized_provider"])
                & (claim_payment_candidates["paid_amount"].round(2) == round(float(claim_dict["claim_amount"]), 2))
            ]

            selected_payment = None
            match_score = 0.0
            status = "failed"
            anomaly_reason = "Missing payment"
            explanation = f"No payment was found for claim {claim_dict['claim_id']}."

            if len(exact_candidates) > 0:
                selected_payment = exact_candidates.iloc[0]
                match_score = 100.0
                status = "fully_matched"
                anomaly_reason = None
                explanation = (
                    f"Exact match on claim ID, provider, and amount. {selected_payment['payment_ref']} clears claim {claim_dict['claim_id']} with zero variance."
                )
            else:
                if not claim_payment_candidates.empty:
                    scored_candidates = []
                    for _, payment in claim_payment_candidates.iterrows():
                        provider_score = fuzz.token_sort_ratio(claim_dict["provider"], payment["provider"])
                        amount_gap = abs(float(claim_dict["claim_amount"]) - float(payment["paid_amount"]))
                        amount_tolerance = max(float(claim_dict["claim_amount"]) * 0.05, 1)
                        amount_score = max(0.0, 100.0 - min(100.0, (amount_gap / amount_tolerance) * 100.0))
                        days_gap = abs((payment["payment_date"] - claim["claim_date"]).days)
                        date_score = max(0.0, 100.0 - min(100.0, days_gap * 12.5))
                        score = round(provider_score * 0.55 + amount_score * 0.25 + date_score * 0.20, 2)
                        scored_candidates.append((score, payment))
                    scored_candidates.sort(key=lambda item: item[0], reverse=True)
                    best_score, best_payment = scored_candidates[0]
                    if best_score >= 70:
                        selected_payment = best_payment
                        match_score = float(best_score)
                        status = "partial_match"
                        anomaly_reason = None
                        explanation = (
                            f"Fuzzy match linked claim {claim_dict['claim_id']} to {selected_payment['payment_ref']} using provider similarity, amount tolerance, and date window."
                        )

            if selected_payment is not None:
                payment_ref = str(selected_payment["payment_ref"])
                matched_payment_refs.add(payment_ref)
                paid_amount = float(selected_payment["paid_amount"])
                payment_date = pd.to_datetime(selected_payment["payment_date"]).date().isoformat()
                if payment_ref in duplicate_payment_refs:
                    status = "anomaly"
                    anomaly_reason = "Duplicate payment"
                    explanation = f"Claim {claim_dict['claim_id']} has multiple SOSYS payments linked to it."
                elif paid_amount > float(claim_dict["claim_amount"]) * 1.2 or paid_amount < float(claim_dict["claim_amount"]) * 0.8:
                    status = "anomaly"
                    anomaly_reason = "Suspicious amount"
                    explanation = (
                        f"Paid amount NPR {paid_amount:,.2f} differs materially from the claim amount NPR {float(claim_dict['claim_amount']):,.2f}."
                    )
                else:
                    anomaly_reason = anomaly_reason if status == "failed" else None

                result_rows.append(
                    {
                        "claim_id": claim_dict["claim_id"],
                        "payment_ref": payment_ref,
                        "provider": claim_dict["provider"],
                        "claim_amount": float(claim_dict["claim_amount"]),
                        "paid_amount": paid_amount,
                        "match_score": match_score,
                        "status": status,
                        "anomaly_reason": anomaly_reason,
                        "explanation": explanation,
                        "payment_date": payment_date,
                        "claim_json": claim_dict["raw_json"],
                        "payment_json": selected_payment["raw_json"],
                    }
                )
            else:
                result_rows.append(
                    {
                        "claim_id": claim_dict["claim_id"],
                        "payment_ref": None,
                        "provider": claim_dict["provider"],
                        "claim_amount": float(claim_dict["claim_amount"]),
                        "paid_amount": None,
                        "match_score": 0.0,
                        "status": "failed",
                        "anomaly_reason": "Missing payment",
                        "explanation": f"Claim {claim_dict['claim_id']} has no matching payment in SOSYS.",
                        "payment_date": None,
                        "claim_json": claim_dict["raw_json"],
                        "payment_json": None,
                    }
                )
                anomaly_counter["missing_payment"] += 1

        ghost_payments = payments[~payments["payment_ref"].astype(str).isin(matched_payment_refs)] if not payments.empty else pd.DataFrame()
        for _, payment in ghost_payments.iterrows():
            if payment["claim_id"] not in set(claims["claim_id"]):
                anomaly_counter["ghost_payment"] += 1
                conn.execute(
                    "INSERT INTO audit_log (event_type, message, claim_id) VALUES (?, ?, ?)",
                    (
                        "ghost_payment",
                        f"Payment {payment['payment_ref']} does not map to a known claim.",
                        payment["claim_id"],
                    ),
                )

        for row in result_rows:
            if row["status"] == "fully_matched":
                pass
            elif row["status"] == "partial_match":
                pass
            elif row["status"] == "anomaly":
                anomaly_counter[row["anomaly_reason"] or "anomaly"] += 1
            elif row["status"] == "failed":
                anomaly_counter[row["anomaly_reason"] or "failed"] += 1

        conn.executemany(
            """
            INSERT INTO reconciliations (
                claim_id, payment_ref, provider, claim_amount, paid_amount, match_score,
                status, anomaly_reason, explanation, payment_date, claim_json, payment_json, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            [
                (
                    row["claim_id"],
                    row["payment_ref"],
                    row["provider"],
                    row["claim_amount"],
                    row["paid_amount"],
                    row["match_score"],
                    row["status"],
                    row["anomaly_reason"],
                    row["explanation"],
                    row["payment_date"],
                    row["claim_json"],
                    row["payment_json"],
                )
                for row in result_rows
            ],
        )

        summary = Counter(row["status"] for row in result_rows)
        anomaly_count = sum(1 for row in result_rows if row["status"] == "anomaly") + anomaly_counter["ghost_payment"]
        return {
            "processed_claims": len(result_rows),
            "fully_matched": summary["fully_matched"],
            "partial_matches": summary["partial_match"],
            "failed": summary["failed"],
            "anomalies": anomaly_count,
        }


def fetch_dashboard() -> dict[str, Any]:
    with connection() as conn:
        claims = pd.read_sql_query("SELECT * FROM reconciliations ORDER BY updated_at DESC", conn)
        uploads = pd.read_sql_query("SELECT * FROM uploads ORDER BY created_at DESC LIMIT 10", conn)
        if claims.empty:
            return {
                "metrics": {"totalClaims": 0, "fullyMatched": 0, "partialMatches": 0, "failed": 0, "anomalies": 0, "matchRate": 0},
                "statusBreakdown": [],
                "trend": [],
                "uploads": uploads.to_dict(orient="records"),
                "recentClaims": [],
                "recentAnomalies": [],
            }

        total = len(claims)
        fully = int((claims["status"] == "fully_matched").sum())
        partial = int((claims["status"] == "partial_match").sum())
        failed = int((claims["status"] == "failed").sum())
        anomalies = int((claims["status"] == "anomaly").sum())
        match_rate = round(((fully + partial) / total) * 100, 2) if total else 0

        claims["bucket"] = claims["status"].map(
            {
                "fully_matched": "Green",
                "partial_match": "Yellow",
                "failed": "Red",
                "anomaly": "Red",
            }
        )
        recent_claims = claims.head(12).to_dict(orient="records")
        recent_anomalies = claims[claims["status"] == "anomaly"].head(8).to_dict(orient="records")

        if "updated_at" in claims.columns:
            trend_frame = claims.copy()
            trend_frame["day"] = pd.to_datetime(trend_frame["updated_at"]).dt.date
            trend = (
                trend_frame.groupby("day")["status"]
                .agg(
                    fully_matched=lambda series: int((series == "fully_matched").sum()),
                    partial_matches=lambda series: int((series == "partial_match").sum()),
                    failed=lambda series: int((series == "failed").sum()),
                    anomalies=lambda series: int((series == "anomaly").sum()),
                )
                .reset_index()
                .sort_values("day")
            )
        else:
            trend = pd.DataFrame(columns=["day", "fully_matched", "partial_matches", "failed", "anomalies"])

        return {
            "metrics": {
                "totalClaims": total,
                "fullyMatched": fully,
                "partialMatches": partial,
                "failed": failed,
                "anomalies": anomalies,
                "matchRate": match_rate,
            },
            "statusBreakdown": [
                {"name": "Fully Matched", "value": fully, "color": CATEGORY_COLORS["fully_matched"]},
                {"name": "Partial Matches", "value": partial, "color": CATEGORY_COLORS["partial_match"]},
                {"name": "Failed/Unmatched", "value": failed, "color": CATEGORY_COLORS["failed"]},
                {"name": "Anomalies", "value": anomalies, "color": CATEGORY_COLORS["anomaly"]},
            ],
            "trend": trend.to_dict(orient="records"),
            "uploads": uploads.to_dict(orient="records"),
            "recentClaims": recent_claims,
            "recentAnomalies": recent_anomalies,
        }


def list_claims(status: str | None = None, search: str | None = None) -> list[dict[str, Any]]:
    with connection() as conn:
        query = "SELECT * FROM reconciliations"
        conditions = []
        params: list[Any] = []
        if status:
            if status == "green":
                conditions.append("status = 'fully_matched'")
            elif status == "yellow":
                conditions.append("status = 'partial_match'")
            elif status == "red":
                conditions.append("status IN ('failed', 'anomaly')")
            elif status == "anomalies":
                conditions.append("status = 'anomaly'")
        if search:
            conditions.append("(claim_id LIKE ? OR provider LIKE ? OR anomaly_reason LIKE ?)")
            like = f"%{search}%"
            params.extend([like, like, like])
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY updated_at DESC, claim_id ASC"
        frame = pd.read_sql_query(query, conn, params=params)
        return frame.to_dict(orient="records")


def get_claim_detail(claim_id: str) -> dict[str, Any] | None:
    with connection() as conn:
        claim = conn.execute("SELECT * FROM claims WHERE claim_id = ?", (claim_id,)).fetchone()
        reconciliation = conn.execute("SELECT * FROM reconciliations WHERE claim_id = ?", (claim_id,)).fetchone()
        if not claim:
            return None
        payment = None
        if reconciliation and reconciliation["payment_ref"]:
            payment = conn.execute("SELECT * FROM payments WHERE payment_ref = ?", (reconciliation["payment_ref"],)).fetchone()
        return {
            "claim": dict(claim),
            "reconciliation": dict(reconciliation) if reconciliation else None,
            "payment": dict(payment) if payment else None,
            "smsMessage": build_sms_message(dict(reconciliation) if reconciliation else None, dict(claim)),
        }


def build_sms_message(reconciliation: dict[str, Any] | None, claim: dict[str, Any]) -> str:
    if not reconciliation:
        return f"Claim {claim['claim_id']} is pending reconciliation."
    status = reconciliation.get("status")
    if status == "fully_matched":
        return f"Claim {claim['claim_id']} reconciled successfully."
    if status == "partial_match":
        return f"Claim {claim['claim_id']} partially paid."
    if status == "anomaly":
        return f"Claim {claim['claim_id']} needs review: {reconciliation.get('anomaly_reason', 'anomaly detected')}."
    return f"Claim {claim['claim_id']} has no matching payment."


RESOLUTION_MAP: dict[str, str] = {
    "Missing payment": (
        "Contact the Social Security Office to verify if the payment was processed but not recorded in SOSYS. "
        "Cross-check with bank statements and request a payment trace using the claim ID."
    ),
    "Duplicate payment": (
        "Flag the duplicate payment ref for recovery. Notify the hospital finance unit and initiate "
        "a refund or adjustment in the next billing cycle. Update SOSYS to mark one payment as void."
    ),
    "Suspicious amount": (
        "Request itemized billing from the hospital for this claim. Compare claimed services against "
        "the payment breakdown. Escalate to the audit team if the variance exceeds 20%."
    ),
    "Ghost payment": (
        "This payment has no matching claim in OpenIMIS. Verify with the hospital whether services were "
        "actually rendered. If unverified, flag for fraud investigation and freeze further disbursements."
    ),
    "No anomaly detected": "No action required. This claim is reconciled and clean.",
}


def get_resolution_for_reason(reason: str | None) -> str:
    if not reason:
        return RESOLUTION_MAP["No anomaly detected"]
    for key, resolution in RESOLUTION_MAP.items():
        if key.lower() in reason.lower():
            return resolution
    return (
        "Review the claim and payment records manually. Contact the hospital billing department "
        "for clarification and cross-verify with the district health office."
    )


def list_hospitals() -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT
                provider,
                COUNT(*) AS total_claims,
                SUM(CASE WHEN status = 'fully_matched' THEN 1 ELSE 0 END) AS fully_matched,
                SUM(CASE WHEN status = 'partial_match' THEN 1 ELSE 0 END) AS partial_matches,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed,
                SUM(CASE WHEN status = 'anomaly' THEN 1 ELSE 0 END) AS anomalies,
                ROUND(SUM(claim_amount), 2) AS total_claimed,
                ROUND(SUM(COALESCE(paid_amount, 0)), 2) AS total_paid,
                ROUND(
                    CAST(SUM(CASE WHEN status IN ('fully_matched','partial_match') THEN 1 ELSE 0 END) AS REAL)
                    / COUNT(*) * 100, 2
                ) AS match_rate
            FROM reconciliations
            GROUP BY provider
            ORDER BY total_claims DESC
            """
        ).fetchall()
        hospitals = []
        for row in rows:
            d = dict(row)
            d["unresolved_issues"] = d["failed"] + d["anomalies"]
            hospitals.append(d)
        return hospitals


def get_hospital_detail(hospital_name: str) -> dict[str, Any] | None:
    with connection() as conn:
        rows = conn.execute(
            "SELECT * FROM reconciliations WHERE provider = ? ORDER BY updated_at DESC",
            (hospital_name,),
        ).fetchall()
        if not rows:
            return None
        claims_list = []
        for row in rows:
            record = dict(row)
            reason = record.get("anomaly_reason")
            record["resolution"] = get_resolution_for_reason(reason)
            claim_raw = json.loads(record.get("claim_json", "{}"))
            record["patient_id"] = claim_raw.get("member_id", "N/A")
            record["diagnosis"] = claim_raw.get("diagnosis", "N/A")
            claims_list.append(record)

        total = len(claims_list)
        fully = sum(1 for c in claims_list if c["status"] == "fully_matched")
        partial = sum(1 for c in claims_list if c["status"] == "partial_match")
        failed = sum(1 for c in claims_list if c["status"] == "failed")
        anomalies = sum(1 for c in claims_list if c["status"] == "anomaly")
        total_claimed = sum(c["claim_amount"] for c in claims_list)
        total_paid = sum(c.get("paid_amount") or 0 for c in claims_list)

        anomaly_reason_counts: Counter = Counter()
        for c in claims_list:
            if c["anomaly_reason"]:
                anomaly_reason_counts[c["anomaly_reason"]] += 1

        return {
            "hospital": hospital_name,
            "summary": {
                "total_claims": total,
                "fully_matched": fully,
                "partial_matches": partial,
                "failed": failed,
                "anomalies": anomalies,
                "total_claimed": round(total_claimed, 2),
                "total_paid": round(total_paid, 2),
                "match_rate": round(((fully + partial) / total) * 100, 2) if total else 0,
                "unresolved_issues": failed + anomalies,
            },
            "anomaly_breakdown": [
                {"reason": reason, "count": count}
                for reason, count in anomaly_reason_counts.most_common()
            ],
            "claims": claims_list,
        }


def send_sms_mock(claim_id: str) -> dict[str, str]:
    detail = get_claim_detail(claim_id)
    if not detail:
        raise ValueError("Claim not found")
    message = detail["smsMessage"]
    with connection() as conn:
        conn.execute(
            "INSERT INTO audit_log (event_type, message, claim_id) VALUES (?, ?, ?)",
            ("sms_sent", message, claim_id),
        )
    return {"claim_id": claim_id, "message": message, "status": "queued"}
