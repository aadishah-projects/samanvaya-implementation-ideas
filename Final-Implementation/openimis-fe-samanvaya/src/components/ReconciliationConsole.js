/**
 * ReconciliationConsole — Upload SOSYS CSV, view matched/unmatched/flagged results.
 */
import React, { useState } from "react";
import {
    Box, Typography, Table, TableBody, TableCell, TableHead, TableRow,
    Button, Chip, Paper, Tabs, Tab, Snackbar, Grid, Card, CardContent,
} from "@material-ui/core";
import { useQuery, useMutation } from "@apollo/client";
import { SAMANVAYA_RECONCILIATION } from "../helpers/graphql/queries";
import { UPLOAD_SOSYS_CSV, RESOLVE_ANOMALY } from "../helpers/graphql/queries";

const npr = (v) => "NPR " + Number(v || 0).toLocaleString("en-IN");

export default function ReconciliationConsole() {
    const [tab, setTab] = useState(0);
    const [snack, setSnack] = useState("");
    const { data, refetch } = useQuery(SAMANVAYA_RECONCILIATION, {
        variables: { matchStatus: tab === 0 ? null : ["MATCHED", "UNMATCHED", "FLAGGED"][tab - 1] },
    });
    const [uploadCsv] = useMutation(UPLOAD_SOSYS_CSV);
    const [resolveAnomaly] = useMutation(RESOLVE_ANOMALY);

    const results = data?.samanvayaReconciliationResults || [];
    const summary = data?.samanvayaReconciliationSummary || {};

    const handleUpload = async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const text = await file.text();
        try {
            const res = await uploadCsv({ variables: { csvContent: text } });
            const d = res.data?.uploadSosysCsv;
            setSnack(d?.message || "Upload complete.");
            refetch();
        } catch (err) { setSnack("Error: " + err.message); }
    };

    const handleResolve = async (logId) => {
        try {
            await resolveAnomaly({ variables: { logId } });
            refetch();
        } catch (e) { setSnack("Error: " + e.message); }
    };

    return (
        <Box p={3}>
            <Typography variant="h4" gutterBottom>Reconciliation Console</Typography>

            <Paper style={{ padding: 16, marginBottom: 24 }}>
                <Button variant="contained" color="primary" component="label">
                    Upload SOSYS CSV
                    <input type="file" accept=".csv" hidden onChange={handleUpload} />
                </Button>
            </Paper>

            {summary.total > 0 && (
                <Grid container spacing={2} style={{ marginBottom: 24 }}>
                    <Grid item xs={3}><Card><CardContent>
                        <Typography variant="h5" style={{ fontWeight: 800 }}>{summary.total}</Typography>
                        <Typography variant="caption">Total</Typography>
                    </CardContent></Card></Grid>
                    <Grid item xs={3}><Card><CardContent>
                        <Typography variant="h5" style={{ fontWeight: 800, color: "#16a34a" }}>{summary.matched}</Typography>
                        <Typography variant="caption">Matched</Typography>
                    </CardContent></Card></Grid>
                    <Grid item xs={3}><Card><CardContent>
                        <Typography variant="h5" style={{ fontWeight: 800, color: "#d97706" }}>{summary.unmatched}</Typography>
                        <Typography variant="caption">Unmatched</Typography>
                    </CardContent></Card></Grid>
                    <Grid item xs={3}><Card><CardContent>
                        <Typography variant="h5" style={{ fontWeight: 800, color: "#dc2626" }}>{summary.flagged}</Typography>
                        <Typography variant="caption">Flagged</Typography>
                    </CardContent></Card></Grid>
                </Grid>
            )}

            <Tabs value={tab} onChange={(_, v) => setTab(v)} style={{ marginBottom: 16 }}>
                <Tab label="All" />
                <Tab label="Matched" />
                <Tab label="Unmatched" />
                <Tab label="Flagged" />
            </Tabs>

            <Table size="small">
                <TableHead>
                    <TableRow>
                        <TableCell>Claim Code</TableCell>
                        <TableCell>Hospital</TableCell>
                        <TableCell align="right">Amount</TableCell>
                        <TableCell align="center">Match</TableCell>
                        <TableCell>Notes</TableCell>
                        <TableCell align="center">Action</TableCell>
                    </TableRow>
                </TableHead>
                <TableBody>
                    {results.map(r => (
                        <TableRow key={r.id} style={{
                            backgroundColor: r.matchStatus === "FLAGGED" ? "#fef2f2" : r.matchStatus === "UNMATCHED" ? "#fffbeb" : "transparent"
                        }}>
                            <TableCell style={{ fontFamily: "monospace", fontSize: 12 }}>{r.claimCode}</TableCell>
                            <TableCell>{r.healthFacility}</TableCell>
                            <TableCell align="right">{npr(r.amount)}</TableCell>
                            <TableCell align="center">
                                <Chip label={r.matchStatus} size="small"
                                    style={{
                                        backgroundColor: r.matchStatus === "MATCHED" ? "#dcfce7" : r.matchStatus === "FLAGGED" ? "#fee2e2" : "#fef3c7",
                                        fontWeight: 700,
                                    }} />
                            </TableCell>
                            <TableCell style={{ fontSize: 12, color: "#666", maxWidth: 300 }}>{r.notes || "—"}</TableCell>
                            <TableCell align="center">
                                {r.matchStatus !== "MATCHED" && !r.resolved ? (
                                    <Button variant="outlined" size="small" onClick={() => handleResolve(r.id)}>Resolve</Button>
                                ) : r.resolved ? (
                                    <Typography variant="caption" style={{ color: "#16a34a", fontWeight: 700 }}>Resolved</Typography>
                                ) : null}
                            </TableCell>
                        </TableRow>
                    ))}
                    {!results.length && (
                        <TableRow><TableCell colSpan={6} align="center" style={{ padding: 24, color: "#999" }}>No reconciliation data. Upload a CSV to begin.</TableCell></TableRow>
                    )}
                </TableBody>
            </Table>

            <Snackbar open={!!snack} autoHideDuration={4000} onClose={() => setSnack("")} message={snack} />
        </Box>
    );
}
