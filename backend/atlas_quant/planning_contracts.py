"""Bounded, decimal analytical inputs; no instruction here can send an order."""
from decimal import Decimal
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from .contracts import ResponseModel
from .targets_contracts import Percent, TargetSpec, TargetExposure, TargetSet
from .valuation_contracts import ValuationCut, Mark

Amount = Annotated[str, Field(pattern=r'^(?:0|[1-9]\d{0,11})(?:\.\d{1,8})?$')]
Shock = Annotated[str, Field(pattern=r'^-?(?:0|[1-9]\d{0,3})(?:\.\d{1,6})?$')]
Id = Annotated[str, Field(pattern=r'^[0-9a-f]{32}$')]
Hash = Annotated[str, Field(pattern=r'^[0-9a-f]{64}$')]


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class StrategyBudget(Strict):
    target_id: Hash
    budget: Percent


class TradeRule(Strict):
    listing_id: Id
    quantity_step: Amount
    fixed_fee: Amount
    fee_bps: Amount
    priority: int = Field(ge=0, le=100)

    @model_validator(mode='after')
    def valid(self):
        if Decimal(self.quantity_step) <= 0 or Decimal(self.fee_bps) > 1000:
            raise ValueError('Lote positivo y comisión proporcional de 0 a 1.000 puntos básicos.')
        return self


class PriceShock(Strict):
    instrument_id: Id
    change_percent: Shock

    @model_validator(mode='after')
    def valid(self):
        if not -100 <= Decimal(self.change_percent) <= 1000:
            raise ValueError('Variación de precio entre −100 y +1.000 %.')
        return self


class PlanningInput(Strict):
    kind: Literal['allocation', 'aggregate', 'scenario', 'benchmark']
    expected_revision: int = Field(ge=1)
    expected_targets_revision: int = Field(ge=0)
    cut_id: Hash | None = None
    contribution_eur: Amount = '0'
    contribution_usd: Amount = '0'
    use_existing_cash: bool = False
    rules: list[TradeRule] = Field(default_factory=list, max_length=199)
    strategies: list[StrategyBudget] = Field(default_factory=list, max_length=20)
    price_shocks: list[PriceShock] = Field(default_factory=list, max_length=199)
    usd_eur_change_percent: Shock = '0'
    performance_id: Hash | None = None
    benchmark_name: str = Field(default='', max_length=120)
    benchmark_source: str = Field(default='', max_length=500)
    benchmark_csv: str = Field(default='', max_length=500_000)
    benchmark_basis: Literal['total-return-EUR'] = 'total-return-EUR'
    benchmark_basis_confirmed: bool = False
    commit: bool = False
    preview_token: Hash | None = None

    @model_validator(mode='after')
    def valid(self):
        for values in ([r.listing_id for r in self.rules], [s.target_id for s in self.strategies],
                       [s.instrument_id for s in self.price_shocks]):
            if len(values) != len(set(values)):
                raise ValueError('No repitas cotizaciones, estrategias ni cambios de precio.')
        if self.kind != 'allocation' and (self.rules or self.use_existing_cash or Decimal(self.contribution_eur) or Decimal(self.contribution_usd)):
            raise ValueError('Las aportaciones, cotizaciones y uso de efectivo solo se admiten en el simulador de asignación.')
        if self.kind not in ('allocation','aggregate') and self.strategies:
            raise ValueError('Los presupuestos de estrategias solo se admiten en agregación o asignación.')
        if self.kind != 'scenario' and (self.price_shocks or Decimal(self.usd_eur_change_percent)):
            raise ValueError('Los cambios hipotéticos solo se admiten en escenarios.')
        if self.kind not in ('allocation','scenario') and self.cut_id:
            raise ValueError('Este análisis no consume un corte de patrimonio.')
        if self.kind != 'benchmark' and (self.performance_id or self.benchmark_csv or self.benchmark_name or self.benchmark_source or self.benchmark_basis_confirmed):
            raise ValueError('Las referencias solo se admiten en comparación de rentabilidad.')
        if sum((Decimal(s.budget) for s in self.strategies), Decimal(0)) > 100:
            raise ValueError('Los presupuestos de estrategias no pueden superar el 100 %.')
        if any(Decimal(s.budget) > 100 for s in self.strategies):
            raise ValueError('Presupuesto fuera de 0–100 %.')
        if not -100 < Decimal(self.usd_eur_change_percent) <= 1000:
            raise ValueError('La variación de EUR por USD debe ser mayor que −100 y como máximo +1.000 %.')
        if self.kind in ('allocation', 'scenario') and not self.cut_id:
            raise ValueError('Selecciona un corte de patrimonio guardado.')
        if self.kind == 'aggregate' and not self.strategies:
            raise ValueError('Selecciona objetivos de estrategias y sus presupuestos.')
        if self.kind == 'benchmark' and not (self.performance_id and self.benchmark_csv and
                self.benchmark_name.strip() and self.benchmark_source.strip() and self.benchmark_basis_confirmed):
            raise ValueError('Selecciona un informe y un CSV identificado; confirma rentabilidad total en EUR.')
        return self


class SimulatedTrade(ResponseModel):
    instrument_id: str
    listing_id: str
    label: str
    side: Literal['buy', 'sell']
    currency: Literal['EUR', 'USD']
    quantity: str
    price: str
    gross_native: str
    fee_native: str
    gross_eur: str
    fee_eur: str
    price_mark: Mark
    fx_mark: Mark | None


class SimulatedCash(ResponseModel):
    currency: Literal['EUR', 'USD']
    initial: str
    contribution: str
    final: str


class AllocationVariant(ResponseModel):
    mode: Literal['contributions', 'rebalance']
    status: Literal['feasible', 'conflicts', 'unavailable']
    provisional: bool
    reasons: list[str]
    trades: list[SimulatedTrade]
    cash: list[SimulatedCash]
    costs_eur: str
    nav_after: str | None
    rows: list[TargetExposure]


class StrategyContribution(ResponseModel):
    target: TargetSet
    budget: str


class CombinedTargets(ResponseModel):
    spec: TargetSpec
    labels: dict[str, str]
    contributors: list[StrategyContribution]
    unassigned_budget: str
    rounding_cash_pp: str
    reasons: list[str]


class AllocationResult(ResponseModel):
    kind: Literal['allocation']
    cut: ValuationCut
    target: TargetSet
    combined: CombinedTargets | None
    variants: list[AllocationVariant]
    reservation_status: Literal['not_implemented']
    sale_proceeds: Literal['hypothetical_settled']


class AggregateResult(ResponseModel):
    kind: Literal['aggregate']
    combined: CombinedTargets


class ScenarioResult(ResponseModel):
    kind: Literal['scenario']
    cut: ValuationCut
    target: TargetSet
    nav_before: str | None
    nav_after: str | None
    change_eur: str | None
    status: Literal['complete', 'provisional', 'unavailable']
    reasons: list[str]
    rows: list[TargetExposure]


class BenchmarkPoint(ResponseModel):
    date: str
    portfolio_index: str
    benchmark_index: str


class BenchmarkResult(ResponseModel):
    kind: Literal['benchmark']
    performance_id: str
    name: str
    source: str
    csv_sha256: str
    basis: Literal['total-return-EUR']
    evidence: Literal['user_declared']
    start_date: str
    end_date: str
    status: Literal['complete', 'provisional']
    portfolio_return: str
    benchmark_return: str
    excess_pp: str
    points: list[BenchmarkPoint]


class PlanningReport(ResponseModel):
    id: str
    portfolio_id: str
    created_at: str
    policy: Literal['atlas-planning-v1']
    context_hash: str
    current: bool
    saved: bool
    inputs: PlanningInput
    result: Annotated[AllocationResult | AggregateResult | ScenarioResult | BenchmarkResult, Field(discriminator='kind')]


class PlanningPreview(ResponseModel):
    report: PlanningReport
    preview_token: str
    committed: bool


class PlanningSummary(ResponseModel):
    id: str
    portfolio_id: str
    created_at: str
    kind: Literal['allocation', 'aggregate', 'scenario', 'benchmark']


class PlanningHistory(ResponseModel):
    reports: list[PlanningSummary]
    offset: int
    limit: int
