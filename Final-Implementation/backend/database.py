import os
from sqlalchemy import create_engine
from sqlalchemy import inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./samanvaya.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def sync_demo_schema():
    """Add demo-only columns when an existing SQLite DB predates the current models."""
    if not DATABASE_URL.startswith("sqlite"):
        return

    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    additions = {
        "claims": {
            "employer": "VARCHAR",
            "employer_esaid": "VARCHAR",
            "scheme": "VARCHAR",
            "ssid": "VARCHAR",
            "relation": "VARCHAR",
            "visit_from": "VARCHAR",
            "visit_to": "VARCHAR",
            "visit_type": "VARCHAR",
            "claimed_date": "VARCHAR",
            "claim_administrator": "VARCHAR",
            "issued_by": "VARCHAR",
            "is_reclaim": "BOOLEAN DEFAULT 0",
            "explanation": "TEXT",
            "policy_information": "TEXT",
            "bank_name": "VARCHAR",
            "branch_name": "VARCHAR",
            "account_name": "VARCHAR",
            "account_no": "VARCHAR",
            "review_status": "VARCHAR",
            "review_notes": "TEXT",
            "reviewed_by": "VARCHAR",
            "reviewed_at": "DATETIME",
            "patient_age": "INTEGER",
            "patient_gender": "VARCHAR",
            "diagnosis": "VARCHAR",
            "treatment_date": "VARCHAR",
        },
        "payment_batches": {
            "batch_code": "VARCHAR",
            "health_facility": "VARCHAR",
        },
        "sosys_legacy_logs": {
            "issue_type": "VARCHAR",
        },
    }

    with engine.begin() as connection:
        for table_name, columns in additions.items():
            if table_name not in table_names:
                continue
            existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, column_type in columns.items():
                if column_name not in existing_columns:
                    connection.execute(
                        text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
                    )

        if "payment_batches" in table_names:
            rows = connection.execute(
                text("SELECT id FROM payment_batches WHERE batch_code IS NULL OR batch_code = ''")
            ).fetchall()
            for index, row in enumerate(rows, start=1):
                connection.execute(
                    text("UPDATE payment_batches SET batch_code = :code WHERE id = :id"),
                    {"code": f"BATCH-LEGACY-{index:04d}", "id": row[0]},
                )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
