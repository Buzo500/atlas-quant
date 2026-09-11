"""Predeclared temporal windows and diagnostic thresholds, never an approval."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from .book import number, decimal_text
from .contracts import ResponseModel

WF_POLICY = 'atlas-walk-forward-fixed-v1'


class WalkForwardConfig(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, frozen=True)
    policy: Literal['atlas-walk-forward-fixed-v1'] = WF_POLICY
    context_sessions: int = Field(default=252, ge=5, le=1000)
    evaluation_sessions: int = Field(default=63, ge=2, le=500)
    minimum_windows: int = Field(default=3, ge=2, le=20)
    minimum_pass_pct: str = Field(default='60', max_length=32)
    maximum_drawdown_pct: str = Field(default='15', max_length=32)
    minimum_fills: int = Field(default=1, ge=1, le=1000)

    @field_validator('minimum_pass_pct', 'maximum_drawdown_pct')
    @classmethod
    def percent(cls, value):
        result = number(value, 'porcentaje', 4, None)
        if result > 100:
            raise ValueError('El porcentaje debe estar entre 0 y 100.')
        return decimal_text(result)


class WalkForwardSummary(ResponseModel):
    status: Literal['meets_criteria', 'does_not_meet', 'insufficient_data']
    windows: int
    evaluable_windows: int
    passing_windows: int
    passing_pct: str
    mean_return_pct: str | None
    mean_excess_pct: str | None
    worst_drawdown_pct: str | None
    reasons: list[str]
