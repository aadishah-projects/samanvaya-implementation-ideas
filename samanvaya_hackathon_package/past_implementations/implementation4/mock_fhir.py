from fastapi import FastAPI
import random
from faker import Faker

app = FastAPI()
fake = Faker()
Faker.seed(42)
random.seed(42)

HOSPITALS = ["Bir Hospital", "Patan Hospital", "Teaching Hospital", "Norvic Hospital", "TU Teaching Hospital"]
MOCK_CLAIMS = []

# Generate 50 realistic FHIR Claim resources
for i in range(1, 51):
    MOCK_CLAIMS.append({
        "resourceType": "Claim",
        "id": f"CLM{i:04d}",
        "status": "active",
        "use": "claim",
        "created": fake.date_between(start_date='-6M', end_date='today').strftime('%Y-%m-%d'),
        "provider": {"display": random.choice(HOSPITALS)},
        "total": {
            "value": random.randint(10000, 150000),
            "currency": "NPR"
        }
    })

# The FHIR standard endpoint for querying Claims
@app.get("/fhir/Claim")
async def get_fhir_claims():
    # FHIR returns data in a "Bundle" structure
    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": len(MOCK_CLAIMS),
        "entry": [{"resource": claim} for claim in MOCK_CLAIMS]
    }

if __name__ == "__main__":
    import uvicorn
    # Run on port 8001
    uvicorn.run(app, host="127.0.0.1", port=8001)