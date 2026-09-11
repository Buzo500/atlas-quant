"""Predeclared one-factor-at-a-time scenarios, no optimizer or risk approval."""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from .book import number, decimal_text
from .contracts import ResponseModel

SENSITIVITY_POLICY = 'atlas-sensitivity-oat-v1'


class SensitivityConfig(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, frozen=True)
    policy: Literal['atlas-sensitivity-oat-v1'] = SENSITIVITY_POLICY
    fast_windows: list[Annotated[int, Field(ge=2, le=249)]] = Field(default_factory=list, max_length=5)
    slow_windows: list[Annotated[int, Field(ge=3, le=250)]] = Field(default_factory=list, max_length=5)
    cost_multipliers: list[Annotated[str, Field(max_length=32)]] = Field(default_factory=lambda: ['1', '2'], max_length=5)

    @field_validator('fast_windows', 'slow_windows')
    @classmethod
    def windows(cls, values):
        if len(set(values)) != len(values):
            raise ValueError('No repitas ventanas dentro del mismo eje.')
        return sorted(values)

    @field_validator('cost_multipliers')
    @classmethod
    def costs(cls, values):
        parsed = [number(value, 'multiplicador de costes', 4, None) for value in values]
        if any(value > 10 for value in parsed) or len(set(parsed)) != len(parsed):
            raise ValueError('Multiplicadores únicos entre 0 y 10.')
        return [decimal_text(value) for value in sorted(parsed)]


class SensitivitySummary(ResponseModel):
    cases: int
    evaluable_cases: int
    min_return_pct: str | None
    max_return_pct: str | None
    return_spread_pp: str | None
    worst_drawdown_pct: str | None
    nonnegative_cases: int
    reasons: list[str]
