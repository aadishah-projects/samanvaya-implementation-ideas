/**
 * ClaimsQueue — View approved claims, create batches, execute payments.
 * Uses Material-UI + Apollo mutations.
 */
import React, { useState } from "react";
import {
    Box, Typography, Table, TableBody, TableCell, TableHead, TableRow,
    Button, Checkbox, Chip, Paper, Snackbar, IconButton,
} from "@material-ui/core";
import { useQuery, useMutation } from "@apollo/client";
import { SAMANVAYA_BATCHES } from "../helpers/graphql/queries";
import { CREATE_PAYMENT_BATCH, EXECUTE_PAYMENT_BATCH } from "../helpers/graphql/queries";

const npr = (v) => "NPR " + Number(v || 0).toLocaleString("en-IN");
const statusColor = { QUEUED: "default", EXECUTING: "primary", DONE: "secondary", PARTIAL: "default", FAILED: "default" };

export default function ClaimsQueue({ rights = [] }) {
    const [selected, setSelected] = useState([]);
    const [snack, setSnack] = useState("");
    const batchesQuery = useQuery(SAMANVAYA_BATCHES, { pollInterval: 3000 });
    const [createBatch] = useMutation(CREATE_PAYMENT_BATCH);
    const [executeBatch] = useMutation(EXECUTE_PAYMENT_BATCH);

    // In real OpenIMIS, approved claims come from the claim module's GraphQL
    // For the module skeleton, we show the batch management UI
    const batches = batchesQuery.data?.samanvayaBatches || [];

    const handleCreateBatch = async () => {
        if (!selected.length) return setSnack("Select at least one claim.");
        try {
            const res = await createBatch({ variables: { claimIds: selected } });
            setSnack(res.data?.createPaymentBatch?.message || "Batch created.");
            setSelected([]);
            batchesQuery.refetch();
        } catch (e) { setSnack("Error: " + e.message); }
    };

    const handleExecute = async (batchId) => {
        try {
            const res = await executeBatch({ variables: { batchId } });
            setSnack(res.data?.executePaymentBatch?.message || "Executed.");
            batchesQuery.refetch();
        } catch (e) { setSnack("Error: " + e.message); }
    };

    return (
        <Box p={3}>
            <Typography variant="h4" gutterBottom>Samanvaya Claims Queue</Typography>

            <Paper style={{ padding: 16, marginBottom: 24 }}>
                <Typography variant="h6" gutterBottom>Payment Batches ({batches.length})</Typography>
                <Table size="small">
                    <TableHead>
                        <TableRow>
                            <TableCell>Batch ID</TableCell>
                            <TableCell align="right">Amount</TableCell>
                            <TableCell align="center">Claims</TableCell>
                            <TableCell align="center">Status</TableCell>
                            <TableCell align="center">Action</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {batches.map(b => (
                            <TableRow key={b.id}>
                                <TableCell style={{ fontFamily: "monospace", fontSize: 12 }}>{b.id.slice(0, 8)}...</TableCell>
                                <TableCell align="right" style={{ fontWeight: 600 }}>{npr(b.totalAmount)}</TableCell>
                                <TableCell align="center">{b.claimCount}</TableCell>
                                <TableCell align="center">
                                    <Chip label={b.status} size="small" color={statusColor[b.status] || "default"} />
                                </TableCell>
                                <TableCell align="center">
                                    {b.status === "QUEUED" && (
                                        <Button variant="contained" color="primary" size="small"
                                            onClick={() => handleExecute(b.id)}>
                                            Execute
                                        </Button>
                                    )}
                                </TableCell>
                            </TableRow>
                        ))}
                        {!batches.length && (
                            <TableRow><TableCell colSpan={5} align="center" style={{ padding: 24, color: "#999" }}>No batches yet</TableCell></TableRow>
                        )}
                    </TableBody>
                </Table>
            </Paper>

            <Snackbar open={!!snack} autoHideDuration={4000} onClose={() => setSnack("")}
                message={snack} />
        </Box>
    );
}
