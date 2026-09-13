"""Pure presentation adapter for immutable D7 reports. No accounting recalculation."""
from datetime import date
from decimal import Decimal, InvalidOperation
import re
from typing import Literal
from pydantic import BaseModel, ConfigDict
from .performance_contracts import (PerformanceReport, PerformanceMetric, PnlMetric,
    TimeWeighted, MoneyWeighted, PerformancePoint, CostItem, PerformanceSources)
from .valuation_contracts import ExternalFlow
from .quality import digest


class PeriodReport(BaseModel):
    model_config = ConfigDict(extra='forbid')
    format: Literal['atlas-period-report-v1'] = 'atlas-period-report-v1'
    kind: Literal['portfolio_performance'] = 'portfolio_performance'
    currency: Literal['EUR'] = 'EUR'
    source_id: str
    source_hash: str
    portfolio_id: str
    portfolio_revision: int
    source_policy: Literal['atlas-performance-v1']
    context_hash: str
    source_context: PerformanceSources
    period_semantics: Literal['closing_interval'] = 'closing_interval'
    start_date: str
    end_date: str
    initial_nav: str | None
    final_nav: str | None
    external_net: PerformanceMetric
    pnl: PnlMetric
    twr: TimeWeighted
    mwr: MoneyWeighted
    costs_eur: PerformanceMetric
    curve: list[PerformancePoint]
    flows: list[ExternalFlow]
    costs: list[CostItem]
    historical_known: bool
    unlinked_payments: list[str]
    initial_state: None = None
    final_state: None = None
    movements: None = None
    benchmark: None = None
    detail_reason: Literal['not_preserved_in_source_report'] = 'not_preserved_in_source_report'
    benchmark_reason: Literal['not_in_source_report'] = 'not_in_source_report'
    economic_hash: str


def adapt(source):
    report = PerformanceReport.model_validate(source)
    if not report.saved:
        raise ValueError('Guarda el informe D7 antes de exportarlo.')
    days = (date.fromisoformat(report.end_date) - date.fromisoformat(report.start_date)).days
    if not 0 < days <= 3660:
        raise ValueError('Periodo guardado no válido.')
    # Source strings become CSV/TeX numbers only after lexical and finite checks.
    # A checksum alone does not make a user-supplied bundle safe to compile.
    def numeric(value):
        if value is None:
            return
        if not isinstance(value,str) or len(value)>160 or not re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d{1,3})?',value):
            raise ValueError('Cantidad no válida en el informe.')
        try:
            number=Decimal(value)
            if not number.is_finite() or abs(number)>Decimal('1e50'):
                raise ValueError('Cantidad fuera de rango de presentación.')
        except InvalidOperation as exc:
            raise ValueError('Cantidad no válida.') from exc
    for value in (report.initial_nav,report.final_nav,report.pnl.display_value): numeric(value)
    for metric in (report.pnl,report.twr,report.mwr,report.costs_eur,report.external_net,*report.twr.segments): numeric(metric.value)
    for point in report.points:
        date.fromisoformat(point.date)
        for value in (point.nav,point.flow_eur,point.twr_factor): numeric(value)
    for item in (*report.flows,*report.costs):
        date.fromisoformat(item.date)
        numeric(item.native_amount); numeric(item.eur_amount)
    for segment in report.twr.segments:
        date.fromisoformat(segment.start_date); date.fromisoformat(segment.end_date)
    # Read-only source validation; retain the original JSON separately, not model_dump output.
    economic = {k:v for k,v in source.items() if k not in ('current', 'saved', 'created_at')}
    values = dict(source_id=report.id, source_hash=digest(source),
        source_policy=report.policy, curve=report.points, economic_hash=digest(economic))
    keys = ('portfolio_id', 'portfolio_revision', 'context_hash', 'source_context',
        'start_date', 'end_date', 'initial_nav', 'final_nav', 'external_net', 'pnl',
        'twr', 'mwr', 'costs_eur', 'flows', 'costs', 'historical_known', 'unlinked_payments')
    return PeriodReport(**values, **{k:getattr(report, k) for k in keys})
