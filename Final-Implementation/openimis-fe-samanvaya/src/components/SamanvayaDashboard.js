/**
 * SamanvayaDashboard — Financial overview with KPI cards, charts, and anomaly alerts.
 * Uses Material-UI + Recharts + Apollo Client.
 */
import React, { useEffect, useRef } from "react";
import { Grid, Card, CardContent, Typography, Box } from "@material-ui/core";
import { useQuery } from "@apollo/client";
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { SAMANVAYA_DASHBOARD_SUMMARY, SAMANVAYA_DASHBOARD_VOLUME, SAMANVAYA_ANOMALY_COUNT } from "../helpers/graphql/queries";

const COLORS = { success: "#16a34a", failed: "#dc2626", pending: "#d97706" };
const npr = (v) => "NPR " + Number(v || 0).toLocaleString("en-IN");

export default function SamanvayaDashboard() {
    const summary = useQuery(SAMANVAYA_DASHBOARD_SUMMARY, { pollInterval: 5000 });
    const volume = useQuery(SAMANVAYA_DASHBOARD_VOLUME, { pollInterval: 5000 });
    const anomalies = useQuery(SAMANVAYA_ANOMALY_COUNT, { pollInterval: 10000 });

    const data = summary.data?.samanvayaDashboardSummary;
    const volData = (volume.data?.samanvayaDashboardVolume || []).reverse();
    const anomalyCount = anomalies.data?.samanvayaAnomalyCount || 0;

    const pieData = data ? [
        { name: "Success", value: data.successCount, color: COLORS.success },
        { name: "Failed", value: data.failedCount, color: COLORS.failed },
        { name: "Pending", value: data.pendingCount, color: COLORS.pending },
    ].filter(d => d.value > 0) : [];

    return (
        <Box p={3}>
            <Typography variant="h4" gutterBottom>Samanvaya Financial Dashboard</Typography>

            {anomalyCount > 0 && (
                <Box mb={2} p={2} bgcolor="#fef2f2" border={1} borderColor="#fca5a5" borderRadius={4}>
                    <Typography variant="body1" style={{ color: "#991b1b", fontWeight: 700 }}>
                        ⚠ {anomalyCount} SOSYS Anomalies Detected — Migration Alert
                    </Typography>
                </Box>
            )}

            <Grid container spacing={2} style={{ marginBottom: 24 }}>
                <KpiCard label="Total Disbursed" value={data ? npr(data.totalDisbursed) : "—"} color="#2563eb" />
                <KpiCard label="Success Rate" value={data ? `${data.successRate}%` : "—"} color="#16a34a" />
                <KpiCard label="Pending" value={data ? data.pendingCount : "—"} color="#d97706" />
                <KpiCard label="Failed" value={data ? data.failedCount : "—"} color="#dc2626" />
            </Grid>

            <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                    <Card>
                        <CardContent>
                            <Typography variant="subtitle2" color="textSecondary" gutterBottom>Payment Breakdown</Typography>
                            {pieData.length > 0 ? (
                                <ResponsiveContainer width="100%" height={220}>
                                    <PieChart>
                                        <Pie data={pieData} cx="50%" cy="50%" outerRadius={80} dataKey="value"
                                            label={({ name, value }) => `${name}: ${value}`}>
                                            {pieData.map((d, i) => <Cell key={i} fill={d.color} />)}
                                        </Pie>
                                        <Tooltip />
                                    </PieChart>
                                </ResponsiveContainer>
                            ) : <Typography color="textSecondary" align="center" style={{ padding: 40 }}>No transactions yet</Typography>}
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} md={6}>
                    <Card>
                        <CardContent>
                            <Typography variant="subtitle2" color="textSecondary" gutterBottom>Daily Volume</Typography>
                            {volData.length > 0 ? (
                                <ResponsiveContainer width="100%" height={220}>
                                    <BarChart data={volData}>
                                        <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                                        <YAxis tick={{ fontSize: 11 }} />
                                        <Tooltip formatter={(v) => npr(v)} />
                                        <Bar dataKey="totalAmount" fill="#2563eb" radius={[4, 4, 0, 0]} />
                                    </BarChart>
                                </ResponsiveContainer>
                            ) : <Typography color="textSecondary" align="center" style={{ padding: 40 }}>No volume data</Typography>}
                        </CardContent>
                    </Card>
                </Grid>
            </Grid>
        </Box>
    );
}

function KpiCard({ label, value, color }) {
    return (
        <Grid item xs={6} md={3}>
            <Card>
                <CardContent>
                    <Typography variant="h5" style={{ fontWeight: 800, color }}>{value}</Typography>
                    <Typography variant="caption" color="textSecondary" style={{ textTransform: "uppercase" }}>{label}</Typography>
                </CardContent>
            </Card>
        </Grid>
    );
}
