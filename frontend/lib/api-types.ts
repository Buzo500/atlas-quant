// Generated from the ATLAS local OpenAPI contracts. Do not edit manually.
// Regenerate: python tools/export_contracts.py
// Verify: python tools/export_contracts.py --check

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

export type CandidateResult = {
  "strategy": Strategy;
  "validation_metrics": Metrics;
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

export type JsonValue = unknown;

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

export type PortfolioPoint = {
  "date": string;
  "nav": number;
  "twr_index": number;
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

export type RiskLimits = {
  "max_position_weight": number;
  "commission_bps": number;
  "slippage_bps": number;
  "minimum_fee": number;
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

export type Summary = {
  "summary": string;
  "limitations": Array<string>;
  "recommendation": "reject" | "continue_observation" | "consider_paper";
  "provider": "none" | "openai" | "anthropic";
  "model"?: (string) | (null);
  "usage"?: (Usage) | (null);
};

export type Trade = {
  "date": string;
  "symbol": string;
  "side": "buy" | "sell";
  "quantity": number;
  "price": number;
  "fee": number;
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
