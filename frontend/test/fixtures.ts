import { vi } from 'vitest';
import type {
  BacktestResponse,
  DatasetResponse,
  ExperimentResponse,
  PortfolioResponse,
  ResearchResponse,
  StateResponse,
} from '@/lib/api-types';

const TEST_TIME = '2026-09-08T12:00:00+00:00';
const TEST_HASH = 'a'.repeat(64);

/** Fresh typed objects: tests can vary a field without sharing mutable state. */
export function dataset(
  id = 'a',
  version = 1,
  overrides: Partial<DatasetResponse> = {},
): DatasetResponse {
  return {
    id,
    name: `Datos ${id}`,
    source_kind: 'synthetic',
    source: 'Fixture local de prueba',
    version,
    updated_at: TEST_TIME,
    manifest: {
      schema_version: '1',
      hash_algorithm: 'sha256',
      hash_version: 1,
      sha256: TEST_HASH,
      name: `Datos ${id}`,
      source_kind: 'synthetic',
      source: 'Fixture local de prueba',
      generated_at: TEST_TIME,
      date_min: '2026-01-01',
      date_max: '2026-09-07',
      symbols: ['A', 'B'],
      row_count: 600,
      counts_by_symbol: { A: 300, B: 300 },
      currencies: ['EUR'],
      synthetic: true,
      price_basis: 'synthetic',
      calendar: 'weekdays_without_exchange_holidays',
      warnings: [],
    },
    ...overrides,
  };
}

export function portfolioResponse(
  overrides: Partial<PortfolioResponse> = {},
): PortfolioResponse {
  return {
    nav: 1000,
    cash: 1000,
    net_contributions: 1000,
    pnl: 0,
    twr: 0,
    positions: [],
    curve: [{ date: '2026-09-07', nav: 1000, twr_index: 1 }],
    warnings: [],
    ...overrides,
  };
}

function backtestResponse(): BacktestResponse {
  return {
    metrics: {
      total_return: 0.02,
      annualized_return: null,
      volatility: 0.01,
      sharpe: null,
      max_drawdown: 0.005,
      trade_count: 1,
      costs: 1.25,
      benchmark_return: 0.01,
      excess_return: 0.01,
      observations: 60,
    },
    curve: [
      { date: '2026-07-01', equity: 1000, benchmark: 1000 },
      { date: '2026-09-07', equity: 1020, benchmark: 1010 },
    ],
    trades: [],
    warnings: [],
    final_cash: 750,
    final_quantity: 2,
    strategy: { kind: 'buy_hold', symbol: 'A' },
    max_position_weight: 0.25,
  };
}

export function researchResponse(
  overrides: Partial<ResearchResponse> = {},
): ResearchResponse {
  return {
    execution: {
      id: 'research-a',
      dataset_id: 'a',
      dataset_name: 'Datos a',
      dataset_version: 1,
      dataset_manifest_hash: TEST_HASH,
      symbol: 'A',
      costs: {
        initial_cash: 10000,
        commission_bps: 5,
        slippage_bps: 5,
        minimum_fee: 1.25,
        max_position_weight: 0.25,
      },
      started_at: TEST_TIME,
      completed_at: '2026-09-08T12:00:01+00:00',
      period: { start: '2026-01-01', end: '2026-09-07', observations: 300 },
    },
    selected_strategy: { kind: 'buy_hold', symbol: 'A' },
    candidate_results: [],
    train_period: { start: '2026-01-01', end: '2026-04-30', observations: 180 },
    validation_period: {
      start: '2026-05-01',
      end: '2026-06-30',
      observations: 60,
    },
    test_period: { start: '2026-07-01', end: '2026-09-07', observations: 60 },
    out_of_sample: backtestResponse(),
    full_result: backtestResponse(),
    sensitivity: [],
    data_hash: TEST_HASH,
    warnings: [],
    max_position_weight: 0.25,
    ...overrides,
  };
}

export function experimentResponse(
  overrides: Partial<ExperimentResponse> = {},
): ExperimentResponse {
  return {
    id: 'experiment-a',
    dataset_id: 'a',
    dataset_version: 1,
    symbol: 'A',
    prompt: 'Experimento sintético de prueba',
    provider: 'none',
    model: null,
    budget_usd: 0,
    hours: 48,
    auto_paper: false,
    costs: {
      initial_cash: 10000,
      commission_bps: 5,
      slippage_bps: 5,
      minimum_fee: 1.25,
      max_position_weight: 0.25,
    },
    policy: {
      min_oos_observations: 126,
      min_trades: 10,
      min_sharpe: 0.5,
      max_drawdown: 0.15,
      min_excess_return: 0,
      min_forward_sessions: 20,
      requested_hours: 48,
    },
    created_at: TEST_TIME,
    status: 'observing',
    phase: 'Observación',
    cutoff: '2026-09-07',
    frozen_hash: TEST_HASH,
    spent_usd: 0,
    reserved_usd: 0,
    summary: null,
    error: null,
    observation: {
      elapsed_hours: 0,
      new_sessions: 0,
      source_kind: 'synthetic',
    },
    gate: null,
    paper_account: null,
    execution_active: false,
    control_requested: null,
    ...overrides,
  };
}

export function stateResponse(
  overrides: Partial<StateResponse> = {},
): StateResponse {
  return {
    datasets: [dataset()],
    experiments: [],
    settings: {
      id: 'main',
      kill_switch: true,
      max_position_weight: 0.25,
      mode: 'paper',
      live_available: false,
    },
    providers: [
      { provider: 'openai', configured: false, models: [] },
      { provider: 'anthropic', configured: false, models: [] },
    ],
    audit: [],
    server_time: TEST_TIME,
    ...overrides,
  };
}

/** Handler receives the API pathname and the original request options. */
export function mockFetch(
  handler: (path: string, init?: RequestInit) => unknown,
) {
  const mocked = vi.fn<typeof fetch>(async (input, init) => {
    const url = input instanceof Request ? input.url : String(input);
    const result = await handler(
      new URL(url, 'http://localhost/').pathname,
      init,
    );
    return result instanceof Response ? result : Response.json(result);
  });
  vi.stubGlobal('fetch', mocked);
  return mocked;
}

export function deferred<T>() {
  let resolve!: (value: T | PromiseLike<T>) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((done, fail) => {
    resolve = done;
    reject = fail;
  });
  return { promise, resolve, reject };
}
