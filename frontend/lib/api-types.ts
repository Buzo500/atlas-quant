// Generated from the ATLAS local OpenAPI contracts. Do not edit manually.
// Regenerate: python tools/export_contracts.py
// Verify: python tools/export_contracts.py --check

export type AggregateResult = {
  "kind": "aggregate";
  "combined": CombinedTargets;
};

export type AliasInput = {
  "expected_revision": number;
  "listing_id": string;
  "provider": string;
  "symbol": string;
  "valid_from"?: (string) | (null);
  "valid_to"?: (string) | (null);
  "source": string;
};

export type AliasResponse = {
  "id": string;
  "listing_id": string;
  "provider": string;
  "symbol": string;
  "valid_from": (string) | (null);
  "valid_to": (string) | (null);
  "source": string;
};

export type AllocationResult = {
  "kind": "allocation";
  "cut": ValuationCut;
  "target": TargetSet;
  "combined": (CombinedTargets) | (null);
  "variants": Array<AllocationVariant>;
  "reservation_status": "not_implemented";
  "sale_proceeds": "hypothetical_settled";
};

export type AllocationVariant = {
  "mode": "contributions" | "rebalance";
  "status": "feasible" | "conflicts" | "unavailable";
  "provisional": boolean;
  "reasons": Array<string>;
  "trades": Array<SimulatedTrade>;
  "cash": Array<SimulatedCash>;
  "costs_eur": string;
  "nav_after": (string) | (null);
  "rows": Array<TargetExposure>;
};

export type AnalysisFxRef = {
  "id": string;
  "version": number;
};

export type AnalysisFxSource = {
  "ref": AnalysisFxRef;
  "name": string;
  "source": string;
  "sha256": string;
  "date_min": string;
  "date_max": string;
};

export type AssetAnalysisHistory = {
  "reports": Array<AssetAnalysisSummary>;
  "offset": number;
  "limit": number;
};

export type AssetAnalysisInput = {
  "sources": Array<AssetSourceRef>;
  "start_date": string;
  "end_date": string;
  "fx"?: (AnalysisFxRef) | (null);
  "commit"?: boolean;
  "preview_token"?: (string) | (null);
};

export type AssetAnalysisPreview = {
  "report": AssetAnalysisReport;
  "preview_token": string;
  "committed": boolean;
};

export type AssetAnalysisReport = {
  "id": string;
  "created_at": string;
  "policy": "atlas-asset-analysis-v1";
  "context_hash": string;
  "catalog_revision": number;
  "corporate_revision": number;
  "inputs": AssetAnalysisInput;
  "result": AssetAnalysisResult;
  "current": boolean;
  "saved": boolean;
};

export type AssetAnalysisResult = {
  "profiles": Array<AssetProfile>;
  "comparison": AssetComparison;
  "correlations": AssetCorrelations;
  "fx": (AnalysisFxSource) | (null);
  "currency": "EUR";
  "basis": "raw-price-excluding-dividends";
  "annualization_sessions": number;
  "warnings": Array<string>;
};

export type AssetAnalysisSummary = {
  "id": string;
  "created_at": string;
  "start_date": string;
  "end_date": string;
  "names": Array<string>;
};

export type AssetComparison = {
  "start_date": (string) | (null);
  "end_date": (string) | (null);
  "rows": Array<AssetComparisonRow>;
  "points": Array<AssetComparisonPoint>;
  "reasons": Array<string>;
};

export type AssetComparisonPoint = {
  "date": string;
  "indices": Array<string>;
};

export type AssetComparisonRow = {
  "source_key": string;
  "start_eur": string;
  "end_eur": string;
  "price_change_pct": string;
};

export type AssetCorrelations = {
  "method": "pearson-simple-returns";
  "minimum_observations": number;
  "observations": number;
  "intervals": Array<CorrelationInterval>;
  "cells": Array<CorrelationCell>;
  "reasons": Array<string>;
};

export type AssetProfile = {
  "source": AssetSource;
  "status": "complete" | "partial" | "unavailable";
  "reasons": Array<string>;
  "expected_sessions": number;
  "observed_sessions": number;
  "valid_sessions": number;
  "valid_intervals": number;
  "first_date": (string) | (null);
  "last_date": (string) | (null);
  "last_close_native": (string) | (null);
  "last_close_eur": (string) | (null);
  "price_change_pct": (string) | (null);
  "session_volatility_pct": (string) | (null);
  "annualized_volatility_pct": (string) | (null);
  "max_drawdown_pct": (string) | (null);
  "historical_known": boolean;
  "known_dividends": number;
};

export type AssetSource = {
  "key": string;
  "ref": AssetSourceRef;
  "name": string;
  "dataset_name": string;
  "source": string;
  "instrument_id": string;
  "instrument_type": string;
  "listing_id": string;
  "market": (string) | (null);
  "currency": "EUR" | "USD";
  "sha256": string;
  "date_min": string;
  "date_max": string;
  "row_count": number;
};

export type AssetSourceCatalog = {
  "sources": Array<AssetSource>;
  "fx": Array<AnalysisFxSource>;
  "limit": number;
};

export type AssetSourceRef = {
  "kind": "native" | "legacy";
  "id": string;
  "version": number;
  "symbol": string;
};

export type AuditEntry = {
  "seq": number;
  "at": string;
  "event": string;
  "entity": (string) | (null);
  "details": {
  [key: string]: JsonValue;
};
};

export type BacktestPoint = {
  "date": string;
  "equity": number;
  "benchmark": number;
};

export type BacktestResponse = {
  "metrics": Metrics;
  "curve": Array<BacktestPoint>;
  "trades": Array<Trade>;
  "warnings": Array<string>;
  "final_cash": number;
  "final_quantity": number;
  "strategy": Strategy;
  "max_position_weight": number;
};

export type BenchmarkPoint = {
  "date": string;
  "portfolio_index": string;
  "benchmark_index": string;
};

export type BenchmarkResult = {
  "kind": "benchmark";
  "performance_id": string;
  "name": string;
  "source": string;
  "csv_sha256": string;
  "basis": "total-return-EUR";
  "evidence": "user_declared";
  "start_date": string;
  "end_date": string;
  "status": "complete" | "provisional";
  "portfolio_return": string;
  "benchmark_return": string;
  "excess_pp": string;
  "points": Array<BenchmarkPoint>;
};

export type BindingPreview = {
  "quality"?: Array<QualityReport>;
  "portfolio": PortfolioRecord;
  "context": PortfolioCut;
  "value": (IdentifiedValue) | (null);
  "entries": Array<BookEntry>;
  "status": "available" | "unavailable";
  "warnings": Array<string>;
  "committed": boolean;
  "preview_token": string;
};

export type BindingsInput = {
  "bindings": Array<PriceBinding>;
  "commit"?: boolean;
  "preview_token"?: (string) | (null);
};

export type BookBalance = {
  "as_of_date": string;
  "currency": "EUR";
  "cash": string;
  "net_contributions": string;
  "realized_pnl": (string) | (null);
  "positions": Array<BookPosition>;
  "warnings": Array<string>;
};

export type BookContext = {
  "portfolio_id": string;
  "portfolio_revision": number;
  "catalog_revision": number;
  "accounting_policy": "legacy-eur-v1" | "atlas-accounting-v2";
  "as_of_date": string;
};

export type BookDetail = {
  "context": BookContext;
  "balance": BookBalance;
  "entries": Array<BookEntry>;
  "total": number;
  "offset": number;
  "limit": number;
  "sources": Array<BookSource>;
};

export type BookDocument = {
  "id": string;
  "kind": "import" | "reconciliation" | "correction";
  "portfolio_revision": number;
  "catalog_revision": number;
  "as_of_date": string;
  "source": string;
  "source_account": string;
  "created_at": string;
  "status": "recorded" | "matched" | "differences";
  "added": number;
  "duplicates": number;
  "current": boolean;
  "evidence": {
  [key: string]: JsonValue;
};
  "balance": BookBalance;
  "differences": Array<ReconciliationRow>;
};

export type BookDocumentSummary = {
  "id": string;
  "kind": "import" | "reconciliation" | "correction";
  "portfolio_revision": number;
  "catalog_revision": number;
  "as_of_date": string;
  "source": string;
  "source_account": string;
  "created_at": string;
  "status": "recorded" | "matched" | "differences";
  "added": number;
  "duplicates": number;
  "current": boolean;
};

export type BookDocuments = {
  "documents": Array<BookDocumentSummary>;
  "total": number;
  "offset": number;
  "limit": number;
};

export type BookEntry = {
  "event": {
  [key: string]: JsonValue;
};
  "listing_id": (string) | (null);
  "date": string;
  "day_sequence": number;
};

export type BookErrorResponse = {
  "detail": Array<BookIssue>;
};

export type BookIssue = {
  "type": string;
  "msg": string;
  "loc": Array<(string) | (number)>;
};

export type BookPosition = {
  "listing_id": string;
  "quantity": string;
  "cost_basis": string;
};

export type BookPreview = {
  "context": BookContext;
  "balance": BookBalance;
  "entries": Array<BookEntry>;
  "total": number;
  "offset": number;
  "limit": number;
  "sources": Array<BookSource>;
  "added": number;
  "duplicates": number;
  "historical_insertion": boolean;
  "committed": boolean;
  "preview_token": string;
  "document_id": string;
};

export type BookSource = {
  "source": string;
  "source_account": string;
};

export type CandidateResult = {
  "strategy": Strategy;
  "validation_metrics": Metrics;
};

export type CatalogResponse = {
  "revision": number;
  "instruments": Array<InstrumentResponse>;
  "listings": Array<ListingResponse>;
  "aliases": Array<AliasResponse>;
};

export type CombinedTargets = {
  "spec": TargetSpec;
  "labels": {
  [key: string]: string;
};
  "contributors": Array<StrategyContribution>;
  "unassigned_budget": string;
  "rounding_cash_pp": string;
  "reasons": Array<string>;
};

export type ControlInput = {
  "action": "pause" | "resume" | "cancel";
};

export type CorporateAction = {
  "date": string;
  "symbol": string;
  "kind": "dividend" | "split" | "capital_gain";
  "value": number;
  "currency": "EUR";
  "applied_to_ledger": false;
};

export type CorporateApplication = {
  "event_id": string;
  "event_revision": number;
  "revision": number;
  "portfolio_revision": number;
  "source": string;
  "source_account": string;
  "event_type": "dividend" | "split";
  "effective_date": string;
  "day_sequence": number;
  "eligible_quantity": (string) | (null);
  "basis_quantity": string;
  "gross_amount": (string) | (null);
  "movement_key": (string) | (null);
  "movement_fingerprint": (string) | (null);
  "basis_hash": string;
  "cancelled": boolean;
  "evidence": string;
  "discrepancy_reason": string;
  "gross_explanation": string;
  "fraction_evidence": string;
  "event_snapshot": CorporateEvent;
  "current": boolean;
  "status": "pending_payment" | "reconciled" | "applied" | "outdated" | "cancelled";
  "receivable": string;
  "price_status": "not_applicable" | "compatible" | "not_accredited";
  "warnings": Array<string>;
};

export type CorporateApplicationInput = {
  "expected_revision": number;
  "commit"?: boolean;
  "preview_token"?: (string) | (null);
  "offset"?: number;
  "limit"?: number;
  "event_id": string;
  "source": string;
  "source_account": string;
  "action"?: "review" | "cancel";
  "review"?: (CorporateReview) | (null);
  "movement_id"?: (string) | (null);
  "reason"?: string;
  "csv"?: string;
};

export type CorporateApplicationPreview = {
  "portfolio_id": string;
  "portfolio_revision": number;
  "corporate_revision": number;
  "as_of_date": string;
  "applications": Array<CorporateApplication>;
  "balance": BookBalance;
  "pending_receivables": string;
  "unlinked_payments": Array<string>;
  "warnings": Array<string>;
  "total": number;
  "offset": number;
  "limit": number;
  "committed": boolean;
  "preview_token": string;
  "document_id": string;
};

export type CorporateCatalog = {
  "revision": number;
  "catalog_revision": number;
  "events": Array<CorporateEvent>;
  "sources": Array<CorporateSource>;
  "total": number;
  "offset": number;
  "limit": number;
};

export type CorporateDocument = {
  "id": string;
  "portfolio_id": (string) | (null);
  "kind": string;
  "created_at": string;
  "evidence": {
  [key: string]: JsonValue;
};
  "result": {
  [key: string]: JsonValue;
};
};

export type CorporateDocumentSummary = {
  "id": string;
  "portfolio_id": (string) | (null);
  "kind": string;
  "created_at": string;
};

export type CorporateDocuments = {
  "documents": Array<CorporateDocumentSummary>;
  "total": number;
  "offset": number;
  "limit": number;
};

export type CorporateEvent = {
  "id": string;
  "revision": number;
  "listing_id": string;
  "event_type": "dividend" | "split";
  "effective_date": (string) | (null);
  "payment_date": (string) | (null);
  "available_at": (string) | (null);
  "gross_per_unit": (string) | (null);
  "currency": "EUR";
  "ratio_numerator": (number) | (null);
  "ratio_denominator": (number) | (null);
  "source_reference": string;
  "verified": boolean;
  "evidence": string;
  "cancelled": boolean;
  "created_at": string;
  "reason": string;
};

export type CorporateInput = {
  "expected_revision": number;
  "commit"?: boolean;
  "preview_token"?: (string) | (null);
  "offset"?: number;
  "limit"?: number;
  "format_id": "atlas-corporate-events-v1";
  "source": string;
  "csv": string;
  "mapping"?: {
  [key: string]: string;
};
  "event_mapping"?: {
  [key: string]: string;
};
  "distinct_reasons"?: {
  [key: string]: string;
};
  "verified"?: boolean;
  "evidence"?: string;
};

export type CorporatePortfolio = {
  "portfolio_id": string;
  "portfolio_revision": number;
  "corporate_revision": number;
  "as_of_date": string;
  "applications": Array<CorporateApplication>;
  "balance": BookBalance;
  "pending_receivables": string;
  "unlinked_payments": Array<string>;
  "warnings": Array<string>;
  "total": number;
  "offset": number;
  "limit": number;
};

export type CorporatePreview = {
  "revision": number;
  "catalog_revision": number;
  "events": Array<CorporateEvent>;
  "sources": Array<CorporateSource>;
  "total": number;
  "offset": number;
  "limit": number;
  "committed": boolean;
  "preview_token": string;
  "document_id": string;
  "added": number;
  "duplicates": number;
};

export type CorporateReview = {
  "event_revision": number;
  "day_sequence": number;
  "evidence": string;
  "eligible_quantity"?: (string) | (null);
  "discrepancy_reason"?: string;
  "gross_amount"?: (string) | (null);
  "gross_explanation"?: string;
  "fraction_evidence"?: string;
};

export type CorporateRevisionInput = {
  "expected_revision": number;
  "commit"?: boolean;
  "preview_token"?: (string) | (null);
  "offset"?: number;
  "limit"?: number;
  "event_id": string;
  "event_revision": number;
  "action": "replace" | "cancel";
  "reason": string;
  "csv"?: string;
  "mapping"?: {
  [key: string]: string;
};
  "verified"?: boolean;
  "evidence"?: string;
};

export type CorporateSource = {
  "source": string;
  "external_id": string;
  "event_id": string;
  "source_reference": string;
  "content_hash": string;
};

export type CorrectionInput = {
  "expected_revision": number;
  "commit"?: boolean;
  "preview_token"?: (string) | (null);
  "offset"?: number;
  "limit"?: number;
  "event_id": string;
  "action": "void" | "replace";
  "reason": string;
  "csv"?: string;
  "mapping"?: {
  [key: string]: string;
};
  "gross_explanations"?: {
  [key: string]: string;
};
  "corporate_mapping"?: {
  [key: string]: string;
};
  "corporate_reviews"?: {
  [key: string]: CorporateReview;
};
  "unaccredited_payments"?: {
  [key: string]: string;
};
};

export type CorrelationCell = {
  "left": string;
  "right": string;
  "value": (string) | (null);
  "reason": (string) | (null);
};

export type CorrelationInterval = {
  "start_date": string;
  "end_date": string;
};

export type CostItem = {
  "event_id": string;
  "date": string;
  "kind": "fee" | "tax" | "charge";
  "currency": "EUR" | "USD";
  "native_amount": string;
  "eur_amount": (string) | (null);
  "status": "complete" | "provisional" | "incomplete";
  "fx": (Mark) | (null);
};

export type Costs = {
  "initial_cash"?: number;
  "commission_bps"?: number;
  "slippage_bps"?: number;
  "minimum_fee"?: number;
  "max_position_weight"?: number;
};

export type CostsResponse = {
  "initial_cash": number;
  "commission_bps": number;
  "slippage_bps": number;
  "minimum_fee": number;
  "max_position_weight": number;
};

export type DatasetPriceBar = {
  "date": string;
  "open": number;
  "high": number;
  "low": number;
  "close": number;
  "volume": number;
};

export type DatasetPricesResponse = {
  "dataset_id": string;
  "dataset_version": number;
  "manifest_hash": string;
  "symbol": string;
  "currency": "EUR";
  "source_kind": "observed" | "synthetic";
  "source": string;
  "source_metadata": (SourceMetadata) | (null);
  "price_basis": string;
  "calendar": string;
  "warnings": Array<string>;
  "available_start": string;
  "available_end": string;
  "first_date": (string) | (null);
  "last_date": (string) | (null);
  "preceding_close": (number) | (null);
  "preceding_date": (string) | (null);
  "bars": Array<DatasetPriceBar>;
};

export type DatasetResponse = {
  "id": string;
  "name": string;
  "source_kind": "observed" | "synthetic";
  "source": string;
  "manifest": Manifest;
  "version": number;
  "updated_at": string;
  "demo"?: (boolean) | (null);
  "feed"?: (FeedResponse) | (null);
  "restored_feed"?: (FeedResponse) | (null);
  "corporate_actions"?: (Array<CorporateAction>) | (null);
  "source_metadata"?: (SourceMetadata) | (null);
  "warnings"?: (Array<string>) | (null);
};

export type EvidenceInput = {
  "symbol": string;
  "calendar_name"?: string;
  "market"?: string;
  "timezone"?: string;
  "calendar_source"?: string;
  "calendar_verified"?: boolean;
  "calendar_csv"?: string;
  "price_basis"?: "raw" | "split_adjusted" | "total_return" | "unknown";
  "basis_verified"?: boolean;
  "basis_source"?: string;
  "availability_csv"?: string;
  "availability_source"?: string;
};

export type EvidencePreview = {
  "dataset_id": string;
  "version": number;
  "committed": boolean;
  "preview_token": string;
  "quality": QualityReport;
};

export type EvidenceRequest = {
  "symbol": string;
  "calendar_name"?: string;
  "market"?: string;
  "timezone"?: string;
  "calendar_source"?: string;
  "calendar_verified"?: boolean;
  "calendar_csv"?: string;
  "price_basis"?: "raw" | "split_adjusted" | "total_return" | "unknown";
  "basis_verified"?: boolean;
  "basis_source"?: string;
  "availability_csv"?: string;
  "availability_source"?: string;
  "expected_version": number;
  "commit"?: boolean;
  "preview_token"?: (string) | (null);
};

export type ExperimentInput = {
  "dataset_id": string;
  "symbol": string;
  "prompt"?: string;
  "provider"?: "none" | "openai" | "anthropic";
  "model"?: (string) | (null);
  "budget_usd"?: number;
  "hours"?: number;
  "auto_paper"?: boolean;
  "costs"?: Costs;
  "policy"?: Policy;
};

export type ExperimentResponse = {
  "quality_policy"?: ("quality-v1") | (null);
  "id": string;
  "dataset_id": string;
  "dataset_version": number;
  "symbol": string;
  "prompt": string;
  "provider": "none" | "openai" | "anthropic";
  "model": (string) | (null);
  "budget_usd": number;
  "hours": number;
  "auto_paper": boolean;
  "costs": CostsResponse;
  "policy": PolicyResponse;
  "created_at": string;
  "status": "queued" | "running" | "observing" | "eligible_paper" | "paused" | "cancelled" | "completed" | "failed" | "interrupted";
  "phase": string;
  "cutoff": string;
  "frozen_hash": string;
  "spent_usd": number;
  "reserved_usd": number;
  "summary": (Summary) | (null);
  "error": (string) | (null);
  "observation": Observation;
  "gate": (Gate) | (null);
  "paper_account": (PaperAccount) | (null);
  "research"?: (ResearchResult) | (null);
  "plan"?: (Plan) | (null);
  "forward_result"?: (BacktestResponse) | (null);
  "started_at"?: (string) | (null);
  "observation_started_at"?: (string) | (null);
  "finished_at"?: (string) | (null);
  "completion_note"?: (string) | (null);
  "resume_status"?: (string) | (null);
  "restored_previous_status"?: (string) | (null);
  "control_requested"?: ("pause" | "cancel") | (null);
  "execution_active"?: boolean;
};

export type ExternalCode = {
  "scheme": string;
  "value": string;
  "source": string;
  "verified"?: boolean;
};

export type ExternalFlow = {
  "event_id": string;
  "date": string;
  "currency": "EUR" | "USD";
  "native_amount": string;
  "eur_amount": (string) | (null);
  "status": "complete" | "provisional" | "incomplete";
  "fx": (Mark) | (null);
};

export type FeedInput = {
  "symbol": string;
  "start": string;
  "end"?: (string) | (null);
};

export type FeedResponse = {
  "symbol": string;
  "start": string;
  "last_attempt": string;
  "error": (string) | (null);
  "interval_hours": number;
};

export type FxBinding = {
  "portfolio_id": string;
  "portfolio_revision": number;
  "series_id": (string) | (null);
  "series_version": (number) | (null);
};

export type FxBindingInput = {
  "expected_revision": number;
  "series_id": string;
  "series_version": number;
  "commit"?: boolean;
  "preview_token"?: (string) | (null);
};

export type FxBindingPreview = {
  "portfolio_id": string;
  "portfolio_revision": number;
  "series_id": (string) | (null);
  "series_version": (number) | (null);
  "committed": boolean;
  "preview_token": string;
};

export type Gate = {
  "passed": boolean;
  "decision": "eligible_paper" | "observe" | "rejected";
  "checks": Array<GateCheck>;
  "limitations": Array<string>;
};

export type GateCheck = {
  "name": string;
  "passed": boolean;
  "actual": JsonValue;
  "required": JsonValue;
  "reason": string;
};

export type HTTPValidationError = {
  "detail"?: Array<ValidationError>;
  [key: string]: unknown;
};

export type HealthResponse = {
  "status": "ok" | "worker_failed";
  "version": string;
  "mode": "local";
  "live_available": false;
  "worker_interval_seconds": number;
};

export type IdentifiedPosition = {
  "symbol": string;
  "quantity": number;
  "price": number;
  "price_date": string;
  "market_value": number;
  "weight": number;
  "cost_basis": number;
  "unrealized_pnl": number;
  "listing_id": string;
};

export type IdentifiedValue = {
  "nav": number;
  "cash": number;
  "net_contributions": number;
  "pnl": number;
  "twr": number;
  "positions": Array<IdentifiedPosition>;
  "curve": Array<PortfolioPoint>;
  "warnings": Array<string>;
};

export type ImportInput = {
  "expected_revision": number;
  "commit"?: boolean;
  "preview_token"?: (string) | (null);
  "offset"?: number;
  "limit"?: number;
  "format_id": "atlas-ledger-v2";
  "source": string;
  "source_account": string;
  "as_of_date": string;
  "csv": string;
  "mapping"?: {
  [key: string]: string;
};
  "gross_explanations"?: {
  [key: string]: string;
};
  "corporate_mapping"?: {
  [key: string]: string;
};
  "corporate_reviews"?: {
  [key: string]: CorporateReview;
};
  "unaccredited_payments"?: {
  [key: string]: string;
};
};

export type InstrumentInput = {
  "expected_revision": number;
  "name": string;
  "instrument_type"?: "equity" | "ETF" | "unknown";
  "source": string;
  "codes"?: Array<ExternalCode>;
  "verified"?: boolean;
};

export type InstrumentResponse = {
  "id": string;
  "name": string;
  "instrument_type": "equity" | "ETF" | "unknown";
  "source": string;
  "verified": boolean;
  "codes": Array<ExternalCode>;
};

export type JsonValue = unknown;

export type LabHistory = {
  "items": Array<LabSummary>;
  "offset": number;
  "limit": number;
};

export type LabInput = {
  "name": string;
  "series_id": string;
  "series_version": number;
  "start_date": string;
  "holdout_date": string;
  "end_date": string;
  "fast"?: number;
  "slow"?: number;
  "sessions_csv": string;
  "opening_source": string;
  "event_free_source": string;
  "evidence_reviewed": boolean;
  "config": SimulationConfig;
};

export type LabMetric = {
  "name": "SMA" | "Comprar y mantener" | "Efectivo";
  "final_nav_eur": (string) | (null);
  "return_pct": (string) | (null);
  "max_drawdown_pct": (string) | (null);
  "fills": number;
  "fees_eur": string;
};

export type LabOpenInput = {
  "protocol_hash": string;
  "acknowledge_exposure": true;
};

export type LabPeriod = {
  "start_date": string;
  "end_date": string;
  "sessions": number;
  "metrics": Array<LabMetric>;
  "curve": Array<LabPoint>;
  "trades": Array<LabTrade>;
  "rejected": number;
  "expired": number;
  "report_hash": string;
};

export type LabPoint = {
  "date": string;
  "sma_eur": (string) | (null);
  "buy_hold_eur": (string) | (null);
  "cash_eur": string;
};

export type LabReport = {
  "protocol": LabSummary;
  "config": SimulationConfig;
  "development": LabPeriod;
  "holdout": (LabPeriod) | (null);
  "warnings": Array<string>;
  "evidence_hash": string;
};

export type LabReproduction = {
  "id": string;
  "development_matches": boolean;
  "holdout_matches": (boolean) | (null);
};

export type LabSummary = {
  "id": string;
  "name": string;
  "created_at": string;
  "policy": "atlas-lab-temporal-v1";
  "instrument_id": string;
  "listing_id": string;
  "series_id": string;
  "series_version": number;
  "source_hash": string;
  "start_date": string;
  "holdout_date": string;
  "end_date": string;
  "opened": boolean;
  "fast": number;
  "slow": number;
};

export type LabTrade = {
  "strategy": "SMA" | "Comprar y mantener";
  "date": string;
  "side": "buy" | "sell";
  "quantity": string;
  "price_eur": string;
  "fee_eur": string;
};

export type LastPrice = {
  "date": string;
  "close": number;
};

export type LedgerInput = {
  "csv": string;
  "commit"?: boolean;
  "preview_token"?: (string) | (null);
};

export type LedgerResponse = {
  "added": number;
  "duplicates": number;
  "total": number;
  "committed": boolean;
  "portfolio": PortfolioResponse;
  "preview_token": string;
};

export type ListingInput = {
  "expected_revision": number;
  "instrument_id": string;
  "currency": "EUR" | "USD";
  "market"?: (string) | (null);
  "calendar"?: (string) | (null);
  "verified"?: boolean;
};

export type ListingResponse = {
  "id": string;
  "instrument_id": string;
  "currency": "EUR" | "USD";
  "market": (string) | (null);
  "calendar": (string) | (null);
  "verified": boolean;
  "legacy_dataset_id"?: (string) | (null);
  "legacy_symbol"?: (string) | (null);
};

export type Manifest = {
  "schema_version": string;
  "hash_algorithm": "sha256";
  "hash_version": number;
  "sha256": string;
  "name": string;
  "source_kind": "observed" | "synthetic";
  "source": string;
  "generated_at": string;
  "date_min": string;
  "date_max": string;
  "symbols": Array<string>;
  "row_count": number;
  "counts_by_symbol": {
  [key: string]: number;
};
  "currencies": Array<string>;
  "synthetic": boolean;
  "price_basis": string;
  "calendar": string;
  "warnings": Array<string>;
};

export type Mark = {
  "status": "complete" | "provisional" | "incomplete";
  "value": (string) | (null);
  "series_id": (string) | (null);
  "version": (number) | (null);
  "sha256": (string) | (null);
  "source": (string) | (null);
  "date": (string) | (null);
  "age_days": (number) | (null);
  "available_at": (string) | (null);
  "historical_known": boolean;
  "reasons": Array<string>;
  "historical_reasons": Array<string>;
};

export type MarketCatalog = {
  "series": Array<MarketSeries>;
};

export type MarketDetail = {
  "series": MarketSeries;
  "evidence": {
  [key: string]: JsonValue;
};
  "observations": Array<MarketObservation>;
  "offset": number;
  "limit": number;
  "total": number;
};

export type MarketImport = {
  "name": string;
  "source": string;
  "series_id"?: (string) | (null);
  "expected_version"?: number;
  "listing_id"?: (string) | (null);
  "listing_ref"?: string;
  "csv": string;
  "evidence"?: (EvidenceInput) | (null);
  "revise_history"?: boolean;
  "reason"?: string;
  "commit"?: boolean;
  "preview_token"?: (string) | (null);
};

export type MarketObservation = {
  "date": string;
  "available_at": (string) | (null);
  "open"?: (string) | (null);
  "high"?: (string) | (null);
  "low"?: (string) | (null);
  "close"?: (string) | (null);
  "volume"?: (string) | (null);
  "rate"?: (string) | (null);
};

export type MarketPreview = {
  "series": MarketSeries;
  "added": number;
  "changed": number;
  "affected_portfolios": Array<string>;
  "committed": boolean;
  "preview_token": string;
};

export type MarketSeries = {
  "id": string;
  "kind": "prices" | "fx";
  "name": string;
  "source": string;
  "version": number;
  "listing_id": (string) | (null);
  "symbol": string;
  "currency": "EUR" | "USD";
  "format_id": "atlas-prices-v2" | "atlas-fx-v1";
  "sha256": string;
  "date_min": string;
  "date_max": string;
  "row_count": number;
  "received_at": string;
  "price_basis": string;
  "basis_verified": boolean;
  "calendar_verified": boolean;
};

export type Metrics = {
  "total_return": number;
  "annualized_return": (number) | (null);
  "volatility": number;
  "sharpe": (number) | (null);
  "max_drawdown": number;
  "trade_count": number;
  "costs": number;
  "benchmark_return": number;
  "excess_return": number;
  "observations": number;
};

export type MoneyWeighted = {
  "value": (string) | (null);
  "status": "complete" | "provisional" | "incomplete" | "unavailable";
  "reasons": Array<string>;
  "convention": "actual-days/365";
  "domain": Array<string>;
  "iterations": number;
  "bracket_width": (string) | (null);
  "normalized_residual": (string) | (null);
  "rate_tolerance": string;
  "residual_tolerance": string;
  "max_iterations": number;
};

export type NativeBalance = {
  "as_of_date": string;
  "balances": Array<NativeCash>;
  "positions": Array<NativePosition>;
  "warnings": Array<string>;
};

export type NativeBookDetail = {
  "context": BookContext;
  "balance": NativeBalance;
  "entries": Array<BookEntry>;
  "total": number;
  "offset": number;
  "limit": number;
  "sources": Array<BookSource>;
};

export type NativeBookDocument = {
  "id": string;
  "kind": "import" | "reconciliation" | "correction";
  "portfolio_revision": number;
  "catalog_revision": number;
  "as_of_date": string;
  "source": string;
  "source_account": string;
  "created_at": string;
  "status": "recorded" | "matched" | "differences";
  "added": number;
  "duplicates": number;
  "current": boolean;
  "evidence": {
  [key: string]: JsonValue;
};
  "balance": NativeBalance;
  "differences": Array<NativeReconciliationRow>;
};

export type NativeBookPreview = {
  "context": BookContext;
  "balance": NativeBalance;
  "entries": Array<BookEntry>;
  "total": number;
  "offset": number;
  "limit": number;
  "sources": Array<BookSource>;
  "added": number;
  "duplicates": number;
  "historical_insertion": boolean;
  "committed": boolean;
  "preview_token": string;
  "document_id": string;
};

export type NativeCash = {
  "currency": "EUR" | "USD";
  "cash": string;
  "net_contributions": string;
  "realized_pnl": (string) | (null);
};

export type NativeCorporateApplication = {
  "event_id": string;
  "event_revision": number;
  "revision": number;
  "portfolio_revision": number;
  "source": string;
  "source_account": string;
  "event_type": "dividend" | "split";
  "effective_date": string;
  "day_sequence": number;
  "eligible_quantity": (string) | (null);
  "basis_quantity": string;
  "gross_amount": (string) | (null);
  "movement_key": (string) | (null);
  "movement_fingerprint": (string) | (null);
  "basis_hash": string;
  "cancelled": boolean;
  "evidence": string;
  "discrepancy_reason": string;
  "gross_explanation": string;
  "fraction_evidence": string;
  "event_snapshot": NativeCorporateEvent;
  "current": boolean;
  "status": "pending_payment" | "reconciled" | "applied" | "outdated" | "cancelled";
  "receivable": string;
  "price_status": "not_applicable" | "compatible" | "not_accredited";
  "warnings": Array<string>;
};

export type NativeCorporateApplicationPreview = {
  "portfolio_id": string;
  "portfolio_revision": number;
  "corporate_revision": number;
  "as_of_date": string;
  "applications": Array<NativeCorporateApplication>;
  "balance": NativeBalance;
  "pending_receivables_by_currency": Array<NativeReceivable>;
  "unlinked_payments": Array<string>;
  "warnings": Array<string>;
  "total": number;
  "offset": number;
  "limit": number;
  "committed": boolean;
  "preview_token": string;
  "document_id": string;
};

export type NativeCorporateCatalog = {
  "revision": number;
  "catalog_revision": number;
  "events": Array<NativeCorporateEvent>;
  "sources": Array<CorporateSource>;
  "total": number;
  "offset": number;
  "limit": number;
};

export type NativeCorporateEvent = {
  "id": string;
  "revision": number;
  "listing_id": string;
  "event_type": "dividend" | "split";
  "effective_date": (string) | (null);
  "payment_date": (string) | (null);
  "available_at": (string) | (null);
  "gross_per_unit": (string) | (null);
  "currency": "EUR" | "USD";
  "ratio_numerator": (number) | (null);
  "ratio_denominator": (number) | (null);
  "source_reference": string;
  "verified": boolean;
  "evidence": string;
  "cancelled": boolean;
  "created_at": string;
  "reason": string;
};

export type NativeCorporatePortfolio = {
  "portfolio_id": string;
  "portfolio_revision": number;
  "corporate_revision": number;
  "as_of_date": string;
  "applications": Array<NativeCorporateApplication>;
  "balance": NativeBalance;
  "pending_receivables_by_currency": Array<NativeReceivable>;
  "unlinked_payments": Array<string>;
  "warnings": Array<string>;
  "total": number;
  "offset": number;
  "limit": number;
};

export type NativeCorporatePreview = {
  "revision": number;
  "catalog_revision": number;
  "events": Array<NativeCorporateEvent>;
  "sources": Array<CorporateSource>;
  "total": number;
  "offset": number;
  "limit": number;
  "committed": boolean;
  "preview_token": string;
  "document_id": string;
  "added": number;
  "duplicates": number;
};

export type NativePosition = {
  "listing_id": string;
  "quantity": string;
  "cost_basis": string;
  "currency": "EUR" | "USD";
};

export type NativeReceivable = {
  "currency": "EUR" | "USD";
  "amount": string;
};

export type NativeReconciliationPreview = {
  "context": BookContext;
  "balance": NativeBalance;
  "status": "matched" | "differences";
  "differences": Array<NativeReconciliationRow>;
  "total": number;
  "offset": number;
  "limit": number;
  "committed": boolean;
  "preview_token": string;
  "document_id": string;
};

export type NativeReconciliationRow = {
  "record_type": "cash" | "position";
  "listing_id": (string) | (null);
  "currency": "EUR" | "USD";
  "book": string;
  "reference": string;
  "difference": string;
  "matched": boolean;
};

export type Observation = {
  "elapsed_hours"?: (number) | (null);
  "new_sessions"?: (number) | (null);
  "source_kind"?: ("observed" | "synthetic") | (null);
  "reconciled"?: (boolean) | (null);
  "forward_metrics"?: (Metrics) | (null);
  "last_date"?: (string) | (null);
};

export type PaperAccount = {
  "mode": "paper";
  "currency": "EUR";
  "initial_cash": number;
  "cash": number;
  "positions": {
  [key: string]: number;
};
  "orders": Array<PaperOrder>;
  "fills": Array<PaperFill>;
  "last_processed_date": string;
  "started_at_date": string;
  "strategy": (Strategy) | (null);
  "equity": number;
  "equity_curve": Array<PaperPoint>;
  "last_price": (number) | (null);
  "last_price_date": (string) | (null);
  "last_prices": {
  [key: string]: LastPrice;
};
  "observed_bars"?: (Array<PriceBar>) | (null);
  "warnings": Array<string>;
  "enabled": boolean;
  "risk_limits"?: (RiskLimits) | (null);
};

export type PaperFill = {
  "date": string;
  "symbol": string;
  "side": "buy" | "sell";
  "quantity": number;
  "price": number;
  "fee": number;
  "id": string;
  "order_id": string;
  "signal_date": string;
  "cash_after": number;
  "position_after": number;
  "position_weight_at_fill": number;
  "simulated": true;
};

export type PaperOrder = {
  "id": string;
  "symbol": string;
  "side": "buy" | "sell";
  "status": "pending" | "filled" | "rejected" | "cancelled";
  "signal_date": string;
  "signal_price": number;
  "quantity": (number) | (null);
  "target_weight": number;
  "execution": "next_observed_open";
  "simulated": true;
  "reason"?: (string) | (null);
  "cancelled_at_date"?: (string) | (null);
  "rejected_at_date"?: (string) | (null);
  "filled_at_date"?: (string) | (null);
  "price"?: (number) | (null);
  "fee"?: (number) | (null);
};

export type PaperPoint = {
  "date": string;
  "equity": number;
  "cash": number;
  "position_value": number;
  "position_weight": number;
  "enabled": boolean;
};

export type PerformanceHistory = {
  "reports": Array<PerformanceSummary>;
  "offset": number;
  "limit": number;
};

export type PerformanceInput = {
  "start_date": string;
  "end_date": string;
  "expected_revision": number;
  "commit"?: boolean;
  "preview_token"?: (string) | (null);
};

export type PerformanceMetric = {
  "value": (string) | (null);
  "status": "complete" | "provisional" | "incomplete" | "unavailable";
  "reasons": Array<string>;
};

export type PerformancePoint = {
  "date": string;
  "nav": (string) | (null);
  "nav_exact": (string) | (null);
  "flow_eur": (string) | (null);
  "status": "complete" | "provisional" | "incomplete";
  "twr_factor": (string) | (null);
  "historical_known": boolean;
  "reasons": Array<string>;
};

export type PerformancePreview = {
  "report": PerformanceReport;
  "committed": boolean;
  "preview_token": string;
};

export type PerformanceReport = {
  "id": string;
  "portfolio_id": string;
  "portfolio_revision": number;
  "context_hash": string;
  "created_at": string;
  "current": boolean;
  "saved": boolean;
  "policy": "atlas-performance-v1";
  "start_date": string;
  "end_date": string;
  "initial_nav": (string) | (null);
  "final_nav": (string) | (null);
  "external_net": PerformanceMetric;
  "pnl": PnlMetric;
  "twr": TimeWeighted;
  "mwr": MoneyWeighted;
  "costs": Array<CostItem>;
  "costs_eur": PerformanceMetric;
  "flows": Array<ExternalFlow>;
  "points": Array<PerformancePoint>;
  "unlinked_payments": Array<string>;
  "historical_known": boolean;
  "source_context": PerformanceSources;
};

export type PerformanceSources = {
  "portfolio_id": string;
  "portfolio_revision": number;
  "catalog_revision": number;
  "corporate_revision": number;
  "bindings": Array<PriceBinding>;
  "fx_binding": (FxBinding) | (null);
  "price_heads": Array<PriceHead>;
  "fx_head": (number) | (null);
};

export type PerformanceSummary = {
  "id": string;
  "portfolio_id": string;
  "portfolio_revision": number;
  "start_date": string;
  "end_date": string;
  "created_at": string;
  "pnl": PnlMetric;
  "twr": PerformanceMetric;
  "mwr": PerformanceMetric;
};

export type Period = {
  "start": string;
  "end": string;
  "observations": number;
};

export type Plan = {
  "hypothesis": string;
  "candidates": Array<Strategy>;
  "risks": Array<string>;
  "horizon_hours"?: (number) | (null);
};

export type PlanningHistory = {
  "reports": Array<PlanningSummary>;
  "offset": number;
  "limit": number;
};

export type PlanningInput = {
  "kind": "allocation" | "aggregate" | "scenario" | "benchmark";
  "expected_revision": number;
  "expected_targets_revision": number;
  "cut_id"?: (string) | (null);
  "contribution_eur"?: string;
  "contribution_usd"?: string;
  "use_existing_cash"?: boolean;
  "rules"?: Array<TradeRule>;
  "strategies"?: Array<StrategyBudget>;
  "price_shocks"?: Array<PriceShock>;
  "usd_eur_change_percent"?: string;
  "performance_id"?: (string) | (null);
  "benchmark_name"?: string;
  "benchmark_source"?: string;
  "benchmark_csv"?: string;
  "benchmark_basis"?: "total-return-EUR";
  "benchmark_basis_confirmed"?: boolean;
  "commit"?: boolean;
  "preview_token"?: (string) | (null);
};

export type PlanningPreview = {
  "report": PlanningReport;
  "preview_token": string;
  "committed": boolean;
};

export type PlanningReport = {
  "id": string;
  "portfolio_id": string;
  "created_at": string;
  "policy": "atlas-planning-v1";
  "context_hash": string;
  "current": boolean;
  "saved": boolean;
  "inputs": PlanningInput;
  "result": (AllocationResult) | (AggregateResult) | (ScenarioResult) | (BenchmarkResult);
};

export type PlanningSummary = {
  "id": string;
  "portfolio_id": string;
  "created_at": string;
  "kind": "allocation" | "aggregate" | "scenario" | "benchmark";
};

export type PnlMetric = {
  "value": (string) | (null);
  "status": "complete" | "provisional" | "incomplete" | "unavailable";
  "reasons": Array<string>;
  "display_value": (string) | (null);
};

export type Policy = {
  "min_oos_observations"?: number;
  "min_trades"?: number;
  "min_sharpe"?: number;
  "max_drawdown"?: number;
  "min_excess_return"?: number;
  "min_forward_sessions"?: number;
};

export type PolicyResponse = {
  "min_oos_observations": number;
  "min_trades": number;
  "min_sharpe": number;
  "max_drawdown": number;
  "min_excess_return": number;
  "min_forward_sessions": number;
  "requested_hours": number;
};

export type PortfolioCut = {
  "portfolio_id": string;
  "portfolio_revision": number;
  "catalog_revision": number;
  "accounting_policy": "legacy-eur-v1" | "atlas-accounting-v2";
  "bindings": Array<PriceBinding>;
  "data_hash": string;
};

export type PortfolioDetail = {
  "quality"?: Array<QualityReport>;
  "portfolio": PortfolioRecord;
  "context": PortfolioCut;
  "value": (IdentifiedValue) | (null);
  "entries": Array<BookEntry>;
  "status": "available" | "unavailable";
  "warnings": Array<string>;
};

export type PortfolioInput = {
  "name": string;
  "accounting_policy"?: "legacy-eur-v1" | "atlas-accounting-v2";
};

export type PortfolioLedgerResponse = {
  "added": number;
  "duplicates": number;
  "total": number;
  "committed": boolean;
  "portfolio": IdentifiedValue;
  "preview_token": string;
};

export type PortfolioPoint = {
  "date": string;
  "nav": number;
  "twr_index": number;
};

export type PortfolioRecord = {
  "id": string;
  "name": string;
  "account_id": string;
  "base_currency": "EUR";
  "accounting_policy": "legacy-eur-v1" | "atlas-accounting-v2";
  "legacy_dataset_id": (string) | (null);
  "revision": number;
  "catalog_revision": number;
  "event_ids": Array<string>;
  "bindings": Array<PriceBinding>;
};

export type PortfolioResponse = {
  "nav": number;
  "cash": number;
  "net_contributions": number;
  "pnl": number;
  "twr": number;
  "positions": Array<Position>;
  "curve": Array<PortfolioPoint>;
  "warnings": Array<string>;
};

export type PortfolioSummary = {
  "id": string;
  "name": string;
  "revision": number;
};

export type Position = {
  "symbol": string;
  "quantity": number;
  "price": number;
  "price_date": string;
  "market_value": number;
  "weight": number;
  "cost_basis": number;
  "unrealized_pnl": number;
};

export type PriceBar = {
  "date": string;
  "symbol": string;
  "currency": "EUR";
  "open": number;
  "high": number;
  "low": number;
  "close": number;
  "volume": number;
};

export type PriceBinding = {
  "listing_id": string;
  "dataset_id": string;
  "dataset_version": number;
  "symbol": string;
};

export type PriceHead = {
  "series_id": string;
  "version": (number) | (null);
};

export type PriceShock = {
  "instrument_id": string;
  "change_percent": string;
};

export type PricesInput = {
  "csv": string;
  "name": string;
  "source": string;
  "source_kind"?: "observed" | "synthetic";
  "dataset_id"?: (string) | (null);
};

export type ProviderModel = {
  "id": string;
  "input_per_million": number;
  "output_per_million": number;
};

export type ProviderResponse = {
  "provider": "openai" | "anthropic";
  "configured": boolean;
  "models": Array<ProviderModel>;
};

export type QualityCapabilities = {
  "draw": "allowed" | "provisional" | "blocked";
  "valuation": "allowed" | "provisional" | "blocked";
  "exploratory": "allowed" | "provisional" | "blocked";
  "historical": "allowed" | "provisional" | "blocked";
  "paper": "allowed" | "provisional" | "blocked";
};

export type QualityDay = {
  "close_at"?: (string) | (null);
  "available_at"?: (string) | (null);
  "date": string;
  "status": "observed_session" | "market_closed" | "calendar_unknown" | "missing_session" | "missing_price" | "stale_mark" | "unexpected_bar";
  "price_date": (string) | (null);
  "age_days": (number) | (null);
  "price": (number) | (null);
  "valuation": "allowed" | "provisional" | "blocked";
  "reasons": Array<string>;
};

export type QualityReport = {
  "calendar_market"?: (string) | (null);
  "calendar_timezone"?: (string) | (null);
  "policy": "quality-v1";
  "dataset_id": string;
  "dataset_version": number;
  "symbol": string;
  "start": string;
  "end": string;
  "evidence_hash": string;
  "calendar_name": (string) | (null);
  "calendar_verified": boolean;
  "calendar_source": (string) | (null);
  "price_basis": "raw" | "split_adjusted" | "total_return" | "unknown";
  "basis_verified": boolean;
  "capabilities": QualityCapabilities;
  "counts": {
  [key: string]: number;
};
  "total_days": number;
  "offset": number;
  "days": Array<QualityDay>;
  "last": QualityDay;
  "warnings": Array<string>;
};

export type ReconciliationInput = {
  "expected_revision": number;
  "commit"?: boolean;
  "preview_token"?: (string) | (null);
  "offset"?: number;
  "limit"?: number;
  "format_id": "atlas-statement-v2";
  "source": string;
  "source_account": string;
  "as_of_date": string;
  "csv": string;
  "mapping"?: {
  [key: string]: string;
};
  "complete_statement": true;
};

export type ReconciliationPreview = {
  "context": BookContext;
  "balance": BookBalance;
  "status": "matched" | "differences";
  "differences": Array<ReconciliationRow>;
  "total": number;
  "offset": number;
  "limit": number;
  "committed": boolean;
  "preview_token": string;
  "document_id": string;
};

export type ReconciliationRow = {
  "record_type": "cash" | "position";
  "listing_id": (string) | (null);
  "currency": "EUR";
  "book": string;
  "reference": string;
  "difference": string;
  "matched": boolean;
};

export type ResearchExecution = {
  "id": string;
  "dataset_id": string;
  "dataset_name": string;
  "dataset_version": number;
  "dataset_manifest_hash": string;
  "symbol": string;
  "costs": CostsResponse;
  "started_at": string;
  "completed_at": string;
  "period": Period;
};

export type ResearchInput = {
  "dataset_id": string;
  "symbol": string;
  "costs"?: Costs;
};

export type ResearchResponse = {
  "selected_strategy": Strategy;
  "candidate_results": Array<CandidateResult>;
  "train_period": Period;
  "validation_period": Period;
  "test_period": Period;
  "out_of_sample": BacktestResponse;
  "full_result": BacktestResponse;
  "sensitivity": Array<SensitivityResult>;
  "data_hash": string;
  "warnings": Array<string>;
  "max_position_weight": number;
  "execution": ResearchExecution;
};

export type ResearchResult = {
  "selected_strategy": Strategy;
  "candidate_results"?: (Array<CandidateResult>) | (null);
  "train_period"?: (Period) | (null);
  "validation_period"?: (Period) | (null);
  "test_period"?: (Period) | (null);
  "out_of_sample"?: (BacktestResponse) | (null);
  "full_result"?: (BacktestResponse) | (null);
  "sensitivity"?: (Array<SensitivityResult>) | (null);
  "data_hash"?: (string) | (null);
  "warnings"?: (Array<string>) | (null);
  "max_position_weight"?: (number) | (null);
  "execution"?: (ResearchExecution) | (null);
};

export type ReturnSegment = {
  "value": (string) | (null);
  "status": "complete" | "provisional" | "incomplete" | "unavailable";
  "reasons": Array<string>;
  "start_date": string;
  "end_date": string;
};

export type RevisionPreview = {
  "dataset_id": string;
  "version": number;
  "committed": boolean;
  "preview_token": string;
  "changed": number;
  "added": number;
  "affected_symbols": Array<string>;
  "feed_paused": boolean;
};

export type RevisionRequest = {
  "expected_version": number;
  "csv": string;
  "reason": string;
  "commit"?: boolean;
  "preview_token"?: (string) | (null);
};

export type RiskLimits = {
  "max_position_weight": number;
  "commission_bps": number;
  "slippage_bps": number;
  "minimum_fee": number;
};

export type ScenarioResult = {
  "kind": "scenario";
  "cut": ValuationCut;
  "target": TargetSet;
  "nav_before": (string) | (null);
  "nav_after": (string) | (null);
  "change_eur": (string) | (null);
  "status": "complete" | "provisional" | "unavailable";
  "reasons": Array<string>;
  "rows": Array<TargetExposure>;
};

export type SensitivityResult = {
  "cost_multiplier": number;
  "period": "test";
  "metrics": Metrics;
};

export type SettingsInput = {
  "kill_switch"?: boolean;
  "max_position_weight"?: number;
};

export type SettingsResponse = {
  "id": string;
  "kill_switch": boolean;
  "max_position_weight": number;
  "mode": "paper";
  "live_available": false;
};

export type SimulatedCash = {
  "currency": "EUR" | "USD";
  "initial": string;
  "contribution": string;
  "final": string;
};

export type SimulatedTrade = {
  "instrument_id": string;
  "listing_id": string;
  "label": string;
  "side": "buy" | "sell";
  "currency": "EUR" | "USD";
  "quantity": string;
  "price": string;
  "gross_native": string;
  "fee_native": string;
  "gross_eur": string;
  "fee_eur": string;
  "price_mark": Mark;
  "fx_mark": (Mark) | (null);
};

export type SimulationConfig = {
  "policy"?: "sma-economics-eur-v1";
  "initial_cash_eur": string;
  "strategy_weight"?: string;
  "max_position_weight"?: string;
  "quantity_step"?: string;
  "fixed_fee_eur"?: string;
  "fee_bps"?: string;
  "slippage_bps"?: string;
  "purchases_enabled"?: boolean;
};

export type SourceMetadata = {
  "provider": string;
  "adapter": string;
  "adapter_version": string;
  "symbol": string;
  "currency": "EUR";
  "currency_verified": boolean;
  "instrument_type": "EQUITY" | "ETF";
  "exchange": (string) | (null);
  "exchange_timezone": (string) | (null);
  "interval": string;
  "is_realtime": boolean;
  "auto_adjust": boolean;
  "back_adjust": boolean;
  "repair": boolean;
  "price_basis": string;
  "start_inclusive": string;
  "end_exclusive": string;
  "fetched_at": string;
  "closed_before_utc_date": string;
  "corporate_actions_present": boolean;
  "corporate_actions_applied": boolean;
  "action_columns": Array<string>;
  "received_rows": number;
  "accepted_rows": number;
  "excluded_out_of_range_rows": number;
  "excluded_empty_quote_rows": number;
  "excluded_empty_quote_dates": Array<string>;
  "documentation": string;
  "request_timeout_seconds": number;
  "fetch_deadline_seconds": number;
};

export type StateResponse = {
  "portfolios"?: Array<PortfolioSummary>;
  "datasets": Array<DatasetResponse>;
  "experiments": Array<ExperimentResponse>;
  "settings": SettingsResponse;
  "providers": Array<ProviderResponse>;
  "audit": Array<AuditEntry>;
  "server_time": string;
};

export type Strategy = {
  "kind": "buy_hold" | "sma_cross" | "momentum";
  "symbol": string;
  "fast_window"?: (number) | (null);
  "slow_window"?: (number) | (null);
  "lookback"?: (number) | (null);
  "top_k"?: (number) | (null);
  "rationale"?: (string) | (null);
};

export type StrategyBudget = {
  "target_id": string;
  "budget": string;
};

export type StrategyContribution = {
  "target": TargetSet;
  "budget": string;
};

export type Summary = {
  "summary": string;
  "limitations": Array<string>;
  "recommendation": "reject" | "continue_observation" | "consider_paper";
  "provider": "none" | "openai" | "anthropic";
  "model"?: (string) | (null);
  "usage"?: (Usage) | (null);
};

export type TargetActivateInput = {
  "expected_revision": number;
  "expected_targets_revision": number;
  "commit"?: boolean;
  "preview_token"?: (string) | (null);
  "target_id": string;
};

export type TargetCashResource = {
  "currency": "EUR" | "USD";
  "native_amount": (string) | (null);
  "eur_value": (string) | (null);
};

export type TargetDraftInput = {
  "expected_revision": number;
  "expected_targets_revision": number;
  "commit"?: boolean;
  "preview_token"?: (string) | (null);
  "spec": TargetSpec;
};

export type TargetEvaluationInput = {
  "expected_revision": number;
  "expected_targets_revision": number;
  "commit"?: boolean;
  "preview_token"?: (string) | (null);
  "cut_id": string;
};

export type TargetExposure = {
  "instrument_id": (string) | (null);
  "label": string;
  "value_eur": (string) | (null);
  "receivable_eur": (string) | (null);
  "weight": (string) | (null);
  "target_weight": string;
  "minimum": (string) | (null);
  "maximum": (string) | (null);
  "concentration_limit": (string) | (null);
  "deviation_pp": (string) | (null);
  "deviation_eur": (string) | (null);
  "reasons": Array<string>;
};

export type TargetHistory = {
  "revision": number;
  "active": (TargetSet) | (null);
  "targets": Array<TargetSet>;
  "offset": number;
  "limit": number;
};

export type TargetPreview = {
  "target": TargetSet;
  "action": "draft" | "activate";
  "preview_token": string;
  "committed": boolean;
};

export type TargetReport = {
  "id": string;
  "portfolio_id": string;
  "created_at": string;
  "policy": "atlas-targets-v1";
  "context_hash": string;
  "current": boolean;
  "saved": boolean;
  "target": TargetSet;
  "cut": ValuationCut;
  "status": "complete" | "provisional" | "unavailable";
  "reasons": Array<string>;
  "rows": Array<TargetExposure>;
  "resources": TargetResources;
};

export type TargetReportPreview = {
  "report": TargetReport;
  "preview_token": string;
  "committed": boolean;
};

export type TargetReportSummary = {
  "id": string;
  "portfolio_id": string;
  "created_at": string;
  "as_of_date": string;
  "target_version": number;
  "status": "complete" | "provisional" | "unavailable";
};

export type TargetReports = {
  "reports": Array<TargetReportSummary>;
  "offset": number;
  "limit": number;
};

export type TargetResources = {
  "cash": Array<TargetCashResource>;
  "committed": null;
  "reservation_status": "not_implemented";
};

export type TargetRow = {
  "instrument_id"?: (string) | (null);
  "weight": string;
  "minimum": string;
  "maximum": string;
  "concentration_limit": string;
};

export type TargetSet = {
  "id": string;
  "portfolio_id": string;
  "version": number;
  "portfolio_revision": number;
  "catalog_revision": number;
  "created_at": string;
  "spec": TargetSpec;
};

export type TargetSpec = {
  "name": string;
  "rows": Array<TargetRow>;
};

export type TimeWeighted = {
  "value": (string) | (null);
  "status": "complete" | "provisional" | "incomplete" | "unavailable";
  "reasons": Array<string>;
  "convention": "daily-external-flows-at-close";
  "start_date": (string) | (null);
  "end_date": string;
  "segments": Array<ReturnSegment>;
};

export type Trade = {
  "date": string;
  "symbol": string;
  "side": "buy" | "sell";
  "quantity": number;
  "price": number;
  "fee": number;
};

export type TradeRule = {
  "listing_id": string;
  "quantity_step": string;
  "fixed_fee": string;
  "fee_bps": string;
  "priority": number;
};

export type Usage = {
  "input_tokens": number;
  "output_tokens": number;
  "estimated_cost_usd": number;
};

export type ValidationError = {
  "loc": Array<(string) | (number)>;
  "msg": string;
  "type": string;
  "input"?: unknown;
  "ctx"?: {
  [key: string]: unknown;
};
  [key: string]: unknown;
};

export type ValuationComponent = {
  "kind": "cash" | "position" | "receivable";
  "reference": string;
  "currency": "EUR" | "USD";
  "quantity": (string) | (null);
  "native_value": (string) | (null);
  "eur_value": (string) | (null);
  "display_eur": (string) | (null);
  "status": "complete" | "provisional" | "incomplete";
  "price": (Mark) | (null);
  "fx": (Mark) | (null);
  "reasons": Array<string>;
};

export type ValuationCut = {
  "id": string;
  "portfolio_id": string;
  "portfolio_revision": number;
  "catalog_revision": number;
  "corporate_revision": number;
  "context_hash": string;
  "policy": "atlas-nav-v1";
  "mode": "reconstruction_at_close";
  "as_of_date": string;
  "decision_at": string;
  "created_at": string;
  "current": boolean;
  "saved": boolean;
  "status": "complete" | "provisional" | "incomplete";
  "value": (string) | (null);
  "exact_value": (string) | (null);
  "known_subtotal": string;
  "rounding_difference": string;
  "balance": NativeBalance;
  "components": Array<ValuationComponent>;
  "flows": Array<ExternalFlow>;
  "reasons": Array<string>;
  "historical_known": boolean;
  "historical_reasons": Array<string>;
};

export type ValuationHistory = {
  "cuts": Array<ValuationSummary>;
  "offset": number;
  "limit": number;
};

export type ValuationInput = {
  "as_of_date": string;
  "decision_at"?: (string) | (null);
  "expected_revision": number;
  "commit"?: boolean;
  "preview_token"?: (string) | (null);
};

export type ValuationPreview = {
  "cut": ValuationCut;
  "preview_token": string;
  "committed": boolean;
};

export type ValuationSummary = {
  "id": string;
  "as_of_date": string;
  "created_at": string;
  "portfolio_revision": number;
  "status": "complete" | "provisional" | "incomplete";
  "value": (string) | (null);
};
