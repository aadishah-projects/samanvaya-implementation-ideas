import pandas as pd

claims = pd.read_csv("claims.csv")
payments = pd.read_csv("payments.csv")

merged = claims.merge(
    payments,
    on="claim_id",
    how="left",
    indicator=True
)

def classify(row):

    if row["_merge"] == "left_only":
        return "🔴 MISSING_PAYMENT"

    if row["amount_claimed"] != row["amount_paid"]:
        return "🔴 AMOUNT_MISMATCH"

    if row["status_y"] != "paid":
        return "🟡 STATUS_PENDING"

    return "🟢 RECONCILED"

merged["reconciliation_status"] = merged.apply(
    classify,
    axis=1
)

# print(
#     merged[
#         [
#             "claim_id",
#             "hospital_name",
#             "amount_claimed",
#             "amount_paid",
#             "reconciliation_status"
#         ]
#     ]
# )
# Save the results to a new CSV file
merged.to_csv("reconciled_output.csv", index=False)
print("✅ Reconciliation complete! Check reconciled_output.csv")