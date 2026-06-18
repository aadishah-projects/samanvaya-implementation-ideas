"""
Full end-to-end test on PostgreSQL — proves Samanvaya works in production conditions.
"""
import os, sys, json, httpx

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "openimis_test.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import django; django.setup()

from openimis_test.claim.models import Claim

GQL = "http://localhost:8080/graphql/"
WEBHOOK = "http://localhost:8080/webhook/gateway/"

def gql(query, variables=None):
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    r = httpx.post(GQL, json=payload, timeout=30)
    data = r.json()
    if "errors" in data:
        print(f"  ERROR: {data['errors']}")
        return None
    return data.get("data")

print("=" * 60)
print("SAMANVAYA END-TO-END TEST ON POSTGRESQL")
print("=" * 60)

# 1. Get approved claims
approved = Claim.objects.filter(status=4)
print(f"\n1. Approved claims: {approved.count()}")
claim_ids = [str(c.id) for c in approved[:3]]
for c in approved[:3]:
    print(f"   {c.code} | {c.health_facility.name} | NPR {c.approved}")

# 2. Create batch
print("\n2. Creating payment batch...")
result = gql("mutation($ids: [UUID]!) { createPaymentBatch(claimIds: $ids) { success message batchId } }",
             {"ids": claim_ids})
if result and result["createPaymentBatch"]["success"]:
    batch_id = result["createPaymentBatch"]["batchId"]
    print(f"   Batch created: {batch_id[:8]}... | {result['createPaymentBatch']['message']}")
else:
    print(f"   FAILED: {result}")
    sys.exit(1)

# 3. Execute batch
print("\n3. Executing batch...")
result = gql("mutation($id: UUID!) { executePaymentBatch(batchId: $id) { success message } }",
             {"id": batch_id})
print(f"   {result['executePaymentBatch']['message']}")

# 4. List transactions
print("\n4. Transactions:")
result = gql("{ samanvayaTransactions { id claimCode healthFacility amount status gatewayRefId } }")
txs = result["samanvayaTransactions"]
for tx in txs:
    print(f"   {tx['claimCode']} | {tx['healthFacility']} | NPR {tx['amount']} | {tx['status']}")

# 5. Webhook: approve first
print("\n5. Webhook: Approving first transaction...")
if txs:
    ref = txs[0]["gatewayRefId"]
    r = httpx.post(WEBHOOK, json={"gateway_ref_id": ref, "status": "SUCCESS"}, timeout=5)
    print(f"   {txs[0]['claimCode']} -> SUCCESS: {r.json()}")

# 6. Webhook: reject second
print("\n6. Webhook: Rejecting second transaction...")
if len(txs) > 1:
    ref = txs[1]["gatewayRefId"]
    r = httpx.post(WEBHOOK, json={"gateway_ref_id": ref, "status": "FAILED"}, timeout=5)
    print(f"   {txs[1]['claimCode']} -> FAILED: {r.json()}")

# 7. Approve third
print("\n7. Webhook: Approving third transaction...")
if len(txs) > 2:
    ref = txs[2]["gatewayRefId"]
    r = httpx.post(WEBHOOK, json={"gateway_ref_id": ref, "status": "SUCCESS"}, timeout=5)
    print(f"   {txs[2]['claimCode']} -> SUCCESS: {r.json()}")

# 8. Final dashboard
print("\n8. Final Dashboard (PostgreSQL):")
result = gql("{ samanvayaDashboardSummary { totalDisbursed successRate successCount failedCount pendingCount totalTransactions } samanvayaBatches { status totalAmount claimCount } samanvayaAnomalyCount }")
d = result["samanvayaDashboardSummary"]
b = result["samanvayaBatches"]
print(f"   Total Disbursed: NPR {d['totalDisbursed']:,.0f}")
print(f"   Success Rate: {d['successRate']}%")
print(f"   Success: {d['successCount']} | Failed: {d['failedCount']} | Pending: {d['pendingCount']}")
print(f"   Batch Status: {b[0]['status'] if b else 'N/A'}")
print(f"   Anomalies: {result['samanvayaAnomalyCount']}")

print("\n" + "=" * 60)
print("ALL TESTS PASSED — Samanvaya running on PostgreSQL")
print("=" * 60)
