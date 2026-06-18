import { gql } from "@apollo/client";

// ── Queries ──────────────────────────────────────────

export const SAMANVAYA_DASHBOARD_SUMMARY = gql`
  query SamanvayaDashboardSummary {
    samanvayaDashboardSummary {
      totalDisbursed
      successRate
      pendingCount
      failedCount
      successCount
      totalTransactions
    }
  }
`;

export const SAMANVAYA_DASHBOARD_VOLUME = gql`
  query SamanvayaDashboardVolume {
    samanvayaDashboardVolume {
      date
      totalAmount
      count
    }
  }
`;

export const SAMANVAYA_ANOMALY_COUNT = gql`
  query SamanvayaAnomalyCount {
    samanvayaAnomalyCount
  }
`;

export const SAMANVAYA_BATCHES = gql`
  query SamanvayaBatches {
    samanvayaBatches {
      id
      createdAt
      totalAmount
      claimCount
      status
    }
  }
`;

export const SAMANVAYA_TRANSACTIONS = gql`
  query SamanvayaTransactions($status: String) {
    samanvayaTransactions(status: $status) {
      id
      batch { id }
      claim { id code }
      amount
      status
      idempotencyKey
      gatewayName
      gatewayRefId
      retryCount
      createdAt
      updatedAt
      healthFacility
      claimCode
      rawRequestLog
      rawResponseLog
      webhookReceivedAt
    }
  }
`;

export const SAMANVAYA_TRANSACTION_DETAIL = gql`
  query SamanvayaTransactionDetail($id: UUID!) {
    samanvayaTransactionDetail(id: $id) {
      id
      amount
      status
      idempotencyKey
      gatewayName
      gatewayRefId
      retryCount
      createdAt
      healthFacility
      claimCode
      rawRequestLog
      rawResponseLog
      webhookReceivedAt
    }
  }
`;

export const SAMANVAYA_RECONCILIATION = gql`
  query SamanvayaReconciliation($matchStatus: String) {
    samanvayaReconciliationResults(matchStatus: $matchStatus) {
      id
      claimCode
      healthFacility
      amount
      paymentDate
      sosysStatus
      matchStatus
      notes
      resolved
    }
    samanvayaReconciliationSummary
  }
`;

// ── Mutations ────────────────────────────────────────

export const CREATE_PAYMENT_BATCH = gql`
  mutation CreatePaymentBatch($claimIds: [UUID]!) {
    createPaymentBatch(claimIds: $claimIds) {
      success
      message
      batchId
    }
  }
`;

export const EXECUTE_PAYMENT_BATCH = gql`
  mutation ExecutePaymentBatch($batchId: UUID!) {
    executePaymentBatch(batchId: $batchId) {
      success
      message
    }
  }
`;

export const RETRY_FAILED_TRANSACTION = gql`
  mutation RetryFailedTransaction($transactionId: UUID!) {
    retryFailedTransaction(transactionId: $transactionId) {
      success
      message
    }
  }
`;

export const UPLOAD_SOSYS_CSV = gql`
  mutation UploadSOSYS($csvContent: String!) {
    uploadSosysCsv(csvContent: $csvContent) {
      success
      message
      uploadedCount
      matched
      unmatched
      flagged
    }
  }
`;

export const RESOLVE_ANOMALY = gql`
  mutation ResolveAnomaly($logId: UUID!) {
    resolveReconciliationAnomaly(logId: $logId) {
      success
      message
    }
  }
`;
