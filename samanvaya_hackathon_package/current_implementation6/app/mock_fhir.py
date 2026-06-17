from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import random
from faker import Faker

app = FastAPI()
fake = Faker()
Faker.seed(42)
random.seed(42)

HOSPITALS = ["Bir Hospital", "Patan Hospital", "Teaching Hospital", "Norvic Hospital", "TU Teaching Hospital"]
MOCK_CLAIMS = []
MOCK_PAYMENTS = []

for i in range(1, 51):
    MOCK_CLAIMS.append({
        "resourceType": "Claim",
        "id": f"C{i:04d}",
        "status": "active",
        "use": "claim",
        "created": fake.date_between(start_date='-6M', end_date='today').strftime('%Y-%m-%d'),
        "provider": {"display": random.choice(HOSPITALS)},
        "total": {
            "value": random.randint(10000, 150000),
            "currency": "NPR"
        }
    })

for index, claim in enumerate(MOCK_CLAIMS, start=1):
    if index <= 12:
        continue

    paid_value = claim["total"]["value"]
    payment_status = "paid"

    if 13 <= index <= 21:
        paid_value = int(claim["total"]["value"] * random.uniform(0.55, 0.9))
    elif 22 <= index <= 26:
        payment_status = "pending"

    MOCK_PAYMENTS.append({
        **claim,
        "total": {
            "value": paid_value,
            "currency": "NPR"
        },
        "paymentStatus": payment_status,
    })

@app.get("/fhir/Claim")
async def get_fhir_claims():
    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": len(MOCK_PAYMENTS),
        "entry": [{"resource": payment} for payment in MOCK_PAYMENTS]
    }

# GraphQL endpoint for the OpenIMIS extractor
@app.post("/api/graphql")
async def graphql_handler(request: Request):
    body = await request.json()
    query = body.get("query", "")

    if "GetApprovedClaims" in query or "claims" in query:
        edges = []
        for claim in MOCK_CLAIMS:
            edges.append({
                "node": {
                    "uuid": f"uuid-{claim['id']}",
                    "code": claim["id"],
                    "dateClaimed": claim["created"],
                    "claimed": str(claim["total"]["value"]),
                    "status": 4,
                    "healthFacility": {
                        "name": claim["provider"]["display"]
                    }
                }
            })
        return {"data": {"claims": {"edges": edges}}}

    return JSONResponse(content={"error": "Unsupported query"}, status_code=400)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
