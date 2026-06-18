/**
 * PaymentLedger — Full transaction history with filters, detail drawer, retry.
 */
import React, { useState } from "react";
import {
    Box, Typography, Table, TableBody, TableCell, TableHead, TableRow,
    Chip, Button, TextField, MenuItem, Dialog, DialogTitle, DialogContent,
    DialogActions, Snackbar,
} from "@material-ui/core";
import { useQuery, useMutation } from "@apollo/client";
import { SAMANVAYA_TRANSACTIONS } from "../helpers/graphql/queries";
import { RETRY_FAILED_TRANSACTION } from "../helpers/graphql/queries";

const npr = (v) => "NPR " + Number(v || 0).toLocaleString("en-IN");
const statusColor = (s) => ({
    SUCCESS: "#16a34a", FAILED: "#dc2626", PROCESSING: "#2563eb", QUEUED: "#d97706", REVERSED: "#6b7280",
}[s] || "#6b7280");

export default function PaymentLedger() {
    const [statusFilter, setStatusFilter] = useState("");
    const [detail, setDetail] = useState(null);
    const [snack, setSnack] = useState("");

    const { data, refetch } = useQuery(SAMANVAYA_TRANSACTIONS, {
        variables: { status: statusFilter || null },
        pollInterval: 3000,
    });
    const [retryTx] = useMutation(RETRY_FAILED_TRANSACTION);

    const txs = data?.samanvayaTransactions || [];

    const handleRetry = async (txId) => {
        try {
            const res = await retryTx({ variables: { transactionId: txId } });
            setSnack(res.data?.retryFailedTransaction?.message || "Retried.");
            refetch();
        } catch (e) { setSnack("Error: " + e.message); }
    };

    return (
        <Box p={3}>
            <Typography variant="h4" gutterBottom>Transaction Ledger</Typography>

            <Box mb={2}>
                <TextField select label="Status" value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)} size="small" style={{ width: 160 }}>
                    <MenuItem value="">All</MenuItem>
                    <MenuItem value="SUCCESS">Success</MenuItem>
                    <MenuItem value="FAILED">Failed</MenuItem>
                    <MenuItem value="PROCESSING">Processing</MenuItem>
                    <MenuItem value="QUEUED">Queued</MenuItem>
                </TextField>
            </Box>

            <Table size="small">
                <TableHead>
                    <TableRow>
                        <TableCell>Claim</TableCell>
                        <TableCell>Hospital</TableCell>
                        <TableCell align="right">Amount</TableCell>
                        <TableCell align="center">Status</TableCell>
                        <TableCell>Gateway Ref</TableCell>
                        <TableCell>Time</TableCell>
                        <TableCell align="center">Actions</TableCell>
                    </TableRow>
                </TableHead>
                <TableBody>
                    {txs.map(tx => (
                        <TableRow key={tx.id} hover style={{ cursor: "pointer" }} onClick={() => setDetail(tx)}>
                            <TableCell style={{ fontFamily: "monospace", fontSize: 12 }}>{tx.claimCode || "—"}</TableCell>
                            <TableCell>{tx.healthFacility || "—"}</TableCell>
                            <TableCell align="right" style={{ fontWeight: 600 }}>{npr(tx.amount)}</TableCell>
                            <TableCell align="center">
                                <Chip label={tx.status} size="small"
                                    style={{ backgroundColor: statusColor(tx.status), color: "white", fontWeight: 700 }} />
                            </TableCell>
                            <TableCell style={{ fontFamily: "monospace", fontSize: 11, color: "#666" }}>
                                {tx.gatewayRefId ? tx.gatewayRefId.slice(0, 12) + "..." : "—"}
                            </TableCell>
                            <TableCell style={{ fontSize: 12, color: "#666" }}>
                                {new Date(tx.createdAt).toLocaleString()}
                            </TableCell>
                            <TableCell align="center">
                                {tx.status === "FAILED" && (
                                    <Button variant="outlined" size="small" color="secondary"
                                        onClick={(e) => { e.stopPropagation(); handleRetry(tx.id); }}>
                                        Retry
                                    </Button>
                                )}
                            </TableCell>
                        </TableRow>
                    ))}
                    {!txs.length && (
                        <TableRow><TableCell colSpan={7} align="center" style={{ padding: 24, color: "#999" }}>No transactions yet</TableCell></TableRow>
                    )}
                </TableBody>
            </Table>

            {detail && (
                <Dialog open={true} onClose={() => setDetail(null)} maxWidth="sm" fullWidth>
                    <DialogTitle>Transaction Detail</DialogTitle>
                    <DialogContent>
                        <Typography variant="body2"><strong>ID:</strong> {detail.id}</Typography>
                        <Typography variant="body2"><strong>Status:</strong> {detail.status}</Typography>
                        <Typography variant="body2"><strong>Amount:</strong> {npr(detail.amount)}</Typography>
                        <Typography variant="body2"><strong>Idempotency Key:</strong> <code>{detail.idempotencyKey}</code></Typography>
                        <Typography variant="body2"><strong>Gateway Ref:</strong> {detail.gatewayRefId || "—"}</Typography>
                        <Typography variant="body2"><strong>Retries:</strong> {detail.retryCount}</Typography>
                        <Box mt={2}>
                            <Typography variant="subtitle2">Request Log</Typography>
                            <pre style={{ fontSize: 11, background: "#f5f5f5", padding: 8, borderRadius: 4, overflow: "auto", maxHeight: 120 }}>
                                {JSON.stringify(detail.rawRequestLog, null, 2)}
                            </pre>
                        </Box>
                        <Box mt={1}>
                            <Typography variant="subtitle2">Response Log</Typography>
                            <pre style={{ fontSize: 11, background: "#f5f5f5", padding: 8, borderRadius: 4, overflow: "auto", maxHeight: 120 }}>
                                {JSON.stringify(detail.rawResponseLog, null, 2)}
                            </pre>
                        </Box>
                    </DialogContent>
                    <DialogActions>
                        <Button onClick={() => setDetail(null)}>Close</Button>
                    </DialogActions>
                </Dialog>
            )}

            <Snackbar open={!!snack} autoHideDuration={4000} onClose={() => setSnack("")} message={snack} />
        </Box>
    );
}
