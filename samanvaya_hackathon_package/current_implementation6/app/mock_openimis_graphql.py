import random
import uuid
from datetime import date, timedelta

import uvicorn
from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter
from typing import Optional, List
import strawberry

HOSPITALS = [
    "Bir Hospital", "Patan Hospital", "TUTH",
    "Grande International Hospital", "Norvic International",
    "Om Hospital", "Nepal Medical College", "Dhulikhel Hospital",
    "Medicare Hospital", "B&B Hospital", "Alka Hospital",
    "HAMS Hospital", "Vayodha Hospital", "Neuro Hospital",
    "Kathmandu Medical College", "Chitwan Medical College",
    "Biratnagar Eye Hospital", "Pokhara Academy of Health Sciences",
    "Manipal Teaching Hospital", "Scheer Memorial Hospital",
]


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


def make_claim(i: int) -> ClaimEdge:
    base_date = date(2025, 1, 1) + timedelta(days=random.randint(0, 160))
    return ClaimEdge(node=ClaimNode(
        uuid=str(uuid.uuid4()),
        code=f"CLM{i:05d}",
        date_claimed=str(base_date),
        claimed=round(random.uniform(2000, 150000), 2),
        status=4,
        health_facility=HealthFacility(name=random.choice(HOSPITALS))
    ))


@strawberry.type
class Mutation:
    @strawberry.mutation
    def token_auth(self, username: str, password: str) -> str:
        return "mock_jwt_token_for_hackathon"


@strawberry.type
class Query:
    @strawberry.field
    def claims(self, status: Optional[int] = None, first: int = 100) -> ClaimConnection:
        return ClaimConnection(edges=[make_claim(i) for i in range(1, first + 1)])


schema = strawberry.Schema(query=Query, mutation=Mutation)
app = FastAPI()
app.include_router(GraphQLRouter(schema), prefix="/api/graphql")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
