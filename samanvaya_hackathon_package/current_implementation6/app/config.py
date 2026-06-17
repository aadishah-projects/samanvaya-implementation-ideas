import os

USE_LIVE_API = os.getenv("USE_LIVE_API", "False").lower() == "true"

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "samanvaya"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "secret"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5433")),
}

if USE_LIVE_API:
    OPENIMIS_URL = "http://demo.openimis.org/api/graphql"
    JWT_TOKEN = os.getenv("OPENIMIS_JWT_TOKEN", "")
    SOSYS_API_URL = "https://sandbox.mojaloop.io/centralledger/v1/transfers"
    SOSYS_HEADERS = {
        "Content-Type": "application/json",
        "FSPIOP-Source": os.getenv("FSPIOP_SOURCE", "testfsp1"),
    }
else:
    OPENIMIS_URL = os.getenv("MOCK_OPENIMIS_URL", "http://localhost:8001/api/graphql")
    JWT_TOKEN = os.getenv("MOCK_JWT_TOKEN", "mock_openimis_jwt_secret_12345")
    SOSYS_API_URL = os.getenv("MOCK_SOSYS_URL", "http://localhost:8001/fhir/Claim")
    SOSYS_HEADERS = {"Content-Type": "application/json"}
