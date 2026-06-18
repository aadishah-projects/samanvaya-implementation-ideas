/**
 * PaymentStatusWidget — Injected into OpenIMIS's ClaimDetail page.
 * Shows a progress bar: Claim Approved → Queued → Sent to Bank → Confirmed.
 * This is the "Blind Spot Fix" — proves OpenIMIS is no longer blind after approval.
 */
import React from "react";
import { Box, Typography, Stepper, Step, StepLabel } from "@material-ui/core";
import { useQuery } from "@apollo/client";
import { SAMANVAYA_TRANSACTIONS } from "../helpers/graphql/queries";

const STEPS = ["Claim Approved", "Queued in Samanvaya", "Sent to Bank", "Confirmed"];
const STATUS_TO_STEP = { QUEUED: 1, PROCESSING: 2, SUCCESS: 3, FAILED: -1, REVERSED: -1 };

export default function PaymentStatusWidget({ claim }) {
    // Query transactions for this claim
    const { data, loading } = useQuery(SAMANVAYA_TRANSACTIONS, {
        variables: { status: null },
        pollInterval: 3000,
        skip: !claim?.id,
    });

    if (!claim?.id) return null;

    const txs = (data?.samanvayaTransactions || []).filter(
        tx => tx.claim?.id === claim.id
    );

    if (!txs.length) {
        return (
            <Box mt={2} p={2} border={1} borderColor="#e5e7eb" borderRadius={4}>
                <Typography variant="subtitle2" color="textSecondary">
                    Samanvaya: No payment record yet for this claim.
                </Typography>
            </Box>
        );
    }

    const tx = txs[0]; // Most recent transaction
    const activeStep = STATUS_TO_STEP[tx.status] || 0;
    const isFailed = tx.status === "FAILED";

    return (
        <Box mt={2} p={2} border={1} borderColor="#e5e7eb" borderRadius={4}>
            <Typography variant="subtitle2" gutterBottom style={{ fontWeight: 700 }}>
                Samanvaya Payment Status
            </Typography>
            {isFailed ? (
                <Box p={1} bgcolor="#fef2f2" borderRadius={4}>
                    <Typography variant="body2" style={{ color: "#991b1b", fontWeight: 600 }}>
                        Payment Failed — {tx.retryCount > 0 ? `Retried ${tx.retryCount} times` : "Use Retry from Ledger"}
                    </Typography>
                </Box>
            ) : (
                <Stepper activeStep={activeStep} alternativeLabel>
                    {STEPS.map((label, idx) => (
                        <Step key={label} completed={idx < activeStep}>
                            <StepLabel>{label}</StepLabel>
                        </Step>
                    ))}
                </Stepper>
            )}
            <Typography variant="caption" color="textSecondary">
                Ref: {tx.gatewayRefId || "pending"} | Amount: NPR {Number(tx.amount).toLocaleString("en-IN")}
            </Typography>
        </Box>
    );
}
