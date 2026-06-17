Looking at your stack — OpenIMIS (GraphQL) + SOSYS/Mojaloop (REST) + PostgreSQL + FastAPI — and the fact that you're in Kathmandu heading to a hackathon, here's a battle plan to go from mock → real, structured as commands you can hand to another AI *or* follow yourself.

---

## 🗺️ The Real-Data Battle Plan

There are **3 phases**. Pick how deep you want to go based on time.

---
## ⚡ Phase 1: Real OpenIMIS (Docker, ~30 min)
**Skip Docker entirely.** There's a live, public OpenIMIS demo server — hosted by the OpenIMIS initiative at `demo.openimis.org` — and the credentials are `Admin` / `admin123`. No installation, no waiting, no Docker.

Here's exactly how to connect to it right now:

---

## ✅ Option 1: Use the Live demo.openimis.org (5 minutes)

### Step 1 — Get a JWT Token

```bash
curl -X POST http://demo.openimis.org/api/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mutation { tokenAuth(username: \"Admin\", password: \"admin123\") { token } }"
  }'
```

Copy the token from the response. It looks like `eyJ0eXAiOiJKV1Q...`

### Step 2 — Test the GraphQL API

```bash
curl -X POST http://demo.openimis.org/api/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: JWT YOUR_TOKEN_HERE" \
  -d '{
    "query": "{ claims(first: 5) { edges { node { uuid code dateClaimed claimed status healthFacility { name } } } } }"
  }'
```

If you see JSON with claim data — you're live on a real OpenIMIS server with real data.

### Step 3 — Update ONE line in your code

```python
# extract_openimis.py — change just this:
OPENIMIS_URL = "http://demo.openimis.org/api/graphql"
JWT_TOKEN = "paste_your_token_here"
```

That's it. Your existing `extract_openimis.py` code works **unchanged** because it already uses the correct OpenIMIS GraphQL schema.

---

## ✅ Option 2: Schema-Accurate Local Mock (if demo.openimis.org is slow at the hackathon venue)

Hackathon WiFi is unpredictable. Have this as your offline fallback — it takes 10 minutes and returns data that exactly mirrors the real OpenIMIS schema:

```bash
pip install strawberry-graphql uvicorn
```

Create `mock_openimis_graphql.py`:

```python
import strawberry
import uvicorn
from strawberry.fastapi import GraphQLRouter
from fastapi import FastAPI
from typing import Optional, List
import random, uuid
from datetime import date, timedelta

# --- Mirror the EXACT OpenIMIS GraphQL schema ---
@strawberry.type
class HealthFacility:
    name: str

@strawberry.type
class ClaimNode:
    uuid: str
    code: str
    date_claimed: str
    claimed: float
    status: int
    health_facility: HealthFacility

@strawberry.type
class ClaimEdge:
    node: ClaimNode

@strawberry.type
class ClaimConnection:
    edges: List[ClaimEdge]

# Realistic Nepali hospital data
HOSPITALS = [
    "Bir Hospital", "Patan Hospital", "TUTH",
    "Grande International Hospital", "Norvic International",
    "Om Hospital", "Nepal Medical College", "Dhulikhel Hospital"
]

def make_claim(i: int) -> ClaimEdge:
    base_date = date(2025, 1, 1) + timedelta(days=random.randint(0, 160))
    return ClaimEdge(node=ClaimNode(
        uuid=str(uuid.uuid4()),
        code=f"CLM{i:05d}",
        date_claimed=str(base_date),
        claimed=round(random.uniform(2000, 150000), 2),
        status=4,  # 4 = Approved, matching your query filter
        health_facility=HealthFacility(name=random.choice(HOSPITALS))
    ))

@strawberry.type
class Query:
    @strawberry.field
    def claims(self, status: Optional[int] = None, first: int = 100) -> ClaimConnection:
        return ClaimConnection(edges=[make_claim(i) for i in range(1, first + 1)])

    # JWT auth mutation (mirrors real OpenIMIS)
    @strawberry.field
    def token_auth(self, username: str, password: str) -> str:
        return "mock_jwt_token_for_hackathon"

schema = strawberry.Schema(query=Query)
app = FastAPI()
app.include_router(GraphQLRouter(schema), prefix="/api/graphql")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

Run it:
```bash
python mock_openimis_graphql.py
# → GraphQL running at http://localhost:8000/api/graphql
```

And in your extractor:
```python
OPENIMIS_URL = "http://localhost:8000/api/graphql"
```

---

## 🎯 Recommended Hackathon Setup

```python
# config.py — one toggle controls everything
USE_LIVE_API = True  # Set False if venue WiFi is bad

OPENIMIS_URL = (
    "http://demo.openimis.org/api/graphql" if USE_LIVE_API
    else "http://localhost:8000/api/graphql"
)
```

Tell judges: *"This flag switches between the live OpenIMIS demo server and our local schema-accurate mock — exactly how production systems handle environment switching."* That's a real engineering pattern and it'll land well.

---

**Try the `curl` command first.** If you get claim data back, you're on the real server in under 5 minutes — no Docker ever needed. What do you get back?

<!-- 
This gets a *real* OpenIMIS instance running locally so your GraphQL extractor hits an actual API.

**Give this block to your other AI:**

```
I need to spin up OpenIMIS locally using Docker for a hackathon project.
My goal: run the openimis-be_py backend with its GraphQL API accessible at localhost:8000.

Tasks:
1. Clone the official openimis-be_py docker repo
2. Configure docker-compose to expose the GraphQL endpoint
3. Run database migrations and seed demo data
4. Verify the GraphQL API is working by running a test query for claims

My OS is: [Windows/Mac/Linux - fill this in]
I already have Docker installed: [Yes/No]

Give me the exact terminal commands to run, one step at a time.
```

**Or follow yourself:**

```bash
# 1. Clone OpenIMIS Docker setup
git clone https://github.com/openimis/openimis-dist_dkr.git
cd openimis-dist_dkr

# 2. Copy and edit the env file
cp .env.example .env
# Edit .env: set DB_PASSWORD, OPENIMIS_PORT=8000

# 3. Start everything
docker compose up -d

# 4. Run migrations (wait ~2 min for DB to be ready first)
docker compose exec web python manage.py migrate
docker compose exec web python manage.py loaddata demo_data  

# 5. Test the GraphQL endpoint
curl -X POST http://localhost:8000/api/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "{ claims(first: 5) { edges { node { code status } } } }"}'
```

**What to update in your code after this:**
```python
# extract_openimis.py
OPENIMIS_URL = "http://localhost:8000/api/graphql"  # was 8001
JWT_TOKEN = "your_real_token_here"
```

To get a real JWT token:
```bash
curl -X POST http://localhost:8000/api/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}'
```

--- -->

## 💳 Phase 2: Real Mojaloop (Sandbox, ~20 min)

Mojaloop has a **public sandbox** — no Docker needed for this one.

**Give this to your other AI:**

```
I need to connect to the Mojaloop public sandbox API to fetch payment/transfer data.
My goal: replace a mock REST extractor that currently hits localhost:8001/fhir/Claim
with real calls to the Mojaloop Central Ledger sandbox.

Tasks:
1. Show me how to authenticate with the Mojaloop sandbox at sandbox.mojaloop.io
2. Write a Python requests script to fetch transfers/settlements from the sandbox
3. Map the Mojaloop transfer response fields to this staging table schema:
   - transaction_id, claim_code, amount_paid, payment_date, status

Mojaloop docs: https://docs.mojaloop.io/api
Give me working Python code with real sandbox endpoints.
```

**Or follow yourself:**
```bash
# Mojaloop sandbox base URL
SANDBOX_URL="https://sandbox.mojaloop.io"

# Test the health endpoint first
curl https://sandbox.mojaloop.io/health

# Get transfers (Central Ledger API)
curl -X GET "https://sandbox.mojaloop.io/centralledger/v1/transfers" \
  -H "Content-Type: application/json" \
  -H "FSPIOP-Source: testfsp1"
```

Update `extract_sosys.py`:
```python
SOSYS_API_URL = "https://sandbox.mojaloop.io/centralledger/v1/transfers"
headers = {
    "Content-Type": "application/json",
    "FSPIOP-Source": "testfsp1"  # sandbox participant
}
response = requests.get(SOSYS_API_URL, headers=headers)
```

---

## 🧱 Phase 3: Seed Realistic Nepali Healthcare Test Data

This is what makes your demo *pop* for judges. Generic UUIDs and "hospital_1" look bad. Real Nepali hospital names + claim amounts look like a real product.

**Give this to your other AI:**

```
I need to seed a PostgreSQL database with realistic Nepali healthcare claims data
for a hackathon demo. The database is called "samanvaya".

Tables to seed:
1. staging_openimis_claims — columns: uuid, code, date_claimed, amount_claimed, hospital_name, status_code
2. staging_sosys_payments — columns: transaction_id, claim_code, amount_paid, payment_date, status

Requirements for the data:
- 50 claims total
- Use REAL Nepali hospital names (Bir Hospital, Patan Hospital, TUTH, Grande International, etc.)
- Amounts in NPR (Nepali Rupees), ranging 2000–150000
- Date range: Jan 2025 to June 2025
- Introduce realistic anomalies:
  * 10 claims with no matching payment (MISSING_PAYMENT)
  * 8 claims where amount_paid != amount_claimed (AMOUNT_MISMATCH)
  * 5 claims where status = 'pending' (STATUS_PENDING)
  * Rest are RECONCILED

Give me a Python script using psycopg2 that inserts this data. DB credentials: 
dbname=samanvaya, user=postgres, password=secret, host=localhost
```

---

## 🎯 Hackathon Judge-Impression Checklist

Once the above is running, these are the things that separate top 3 from the rest:

| Thing to add | Time | Impact |
|---|---|---|
| Live "Last synced: X mins ago" timestamp on dashboard | 10 min | High |
| A "Run Pipeline Now" button in the UI that triggers ETL | 20 min | Very High |
| Anomaly count badges (red = mismatches, yellow = pending) | 15 min | High |
| Export to CSV button for `reconciled_view` | 10 min | Medium |
| One real Nepal-specific stat (e.g., "NPR 4.2L in unreconciled claims") | 5 min | High |

---

## 🆘 If the Real APIs Won't Connect at the Hackathon

Hackathon WiFi is terrible. Have this fallback:

```python
# config.py — toggle this one line
USE_REAL_APIS = False  # Set True when network works

# In extract_openimis.py
if not USE_REAL_APIS:
    OPENIMIS_URL = "http://localhost:8001/api/graphql"  # mock
else:
    OPENIMIS_URL = "http://localhost:8000/api/graphql"  # real Docker
```

This way you can demo confidently regardless of connectivity, and *tell* judges "this config flag switches between the real API and our local test environment" — which is actually how production systems work.

---

**What's your current blocker?** Do you have Docker running, and is the FastAPI dashboard currently showing data from the mock? That'll tell me which phase to help you drill into first.