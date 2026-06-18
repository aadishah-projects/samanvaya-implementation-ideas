/**
 * Samanvaya — OpenIMIS Frontend Module Entry Point
 * Registers routes, menu items, and default menu configuration.
 */
import SamanvayaDashboard from "./components/SamanvayaDashboard";
import ClaimsQueue from "./components/ClaimsQueue";
import PaymentLedger from "./components/PaymentLedger";
import ReconciliationConsole from "./components/ReconciliationConsole";
import PaymentStatusWidget from "./components/PaymentStatusWidget";
import { RIGHT_DASHBOARD, ROUTE_DASHBOARD, ROUTE_CLAIMS, ROUTE_LEDGER, ROUTE_RECON } from "./constants";

export function getRoutes(cfg) {
    return [
        { path: ROUTE_DASHBOARD, component: SamanvayaDashboard },
        { path: ROUTE_CLAIMS, component: ClaimsQueue },
        { path: ROUTE_LEDGER, component: PaymentLedger },
        { path: ROUTE_RECON, component: ReconciliationConsole },
    ];
}

export function getMenu(cfg) {
    return {
        key: "samanvaya",
        label: "Samanvaya Payments",
        filter: (rights) => rights.includes(RIGHT_DASHBOARD),
        subMenu: [
            { key: "samanvaya.dashboard", label: "Financial Dashboard", path: ROUTE_DASHBOARD },
            { key: "samanvaya.claims", label: "Claims Queue", path: ROUTE_CLAIMS },
            { key: "samanvaya.ledger", label: "Transaction Ledger", path: ROUTE_LEDGER },
            { key: "samanvaya.reconciliation", label: "Reconciliation", path: ROUTE_RECON },
        ],
    };
}

export function getDefaultMenu(cfg) {
    return {
        key: "samanvaya",
        label: "Samanvaya Payments",
        subMenu: [
            { key: "samanvaya.dashboard", label: "Financial Dashboard", path: ROUTE_DASHBOARD },
        ],
    };
}

// Extension point: inject PaymentStatusWidget into ClaimDetail page
export function getExtensions() {
    return {
        "claim.ClaimDetail": [
            {
                component: PaymentStatusWidget,
                position: "after",
            },
        ],
    };
}
