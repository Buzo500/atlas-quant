"""Exploratory inference on frozen development, never a trading permission."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from .candidate_contracts import Hash
from .contracts import ResponseModel
from .lab_contracts import LabSummary, LabMetric
from .simulation_contracts import SimulationConfig

POLICY = 'atlas-robustness-stationary-v1'


class RobustnessInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, str_strip_whitespace=True)
    protocol_id: Hash
    candidate_id: Hash
    revision: int = Field(ge=1, le=100)
    revision_hash: Hash
    related_protocol_ids: list[Hash] = Field(min_length=1, max_length=20)
    reason: str = Field(min_length=10, max_length=2000)
    acknowledge_exploratory: Literal[True]

    @field_validator('acknowledge_exploratory', mode='before')
    @classmethod
    def exact_true(cls, value):
        if value is not True:
            raise ValueError('Confirma el alcance exploratorio y los ensayos declarados.')
        return value

    @field_validator('related_protocol_ids')
    @classmethod
    def distinct(cls, value):
        if len(set(value)) != len(value):
            raise ValueError('No repitas ensayos relacionados.')
        return sorted(value)

    @model_validator(mode='after')
    def main_trial(self):
        if self.protocol_id not in self.related_protocol_ids:
            raise ValueError('Incluye el protocolo principal en los ensayos relacionados.')
        return self


class RobustnessLength(ResponseModel):
    length: int
    principal: bool
    seed: str
    replicas: int
    lower_pp: str
    upper_pp: str
    direction: Literal['positive', 'negative', 'uncertain']
    indices_hash: str


class RobustnessResult(ResponseModel):
    policy: Literal['atlas-robustness-stationary-v1']
    status: Literal['no_evaluable', 'exploratory']
    reasons: list[str]
    warnings: list[str]
    intervals: int
    warmup_sessions: int
    start_date: str | None
    end_date: str | None
    work_indices: int
    mean_excess_pp: str | None
    principal_includes_zero: bool | None
    direction_changes: bool | None
    lengths: list[RobustnessLength]
    nav_hash: str
    returns_hash: str | None
    float_returns_hash: str | None
    prng: str
    numpy_version: str
    master_seed: int
    result_hash: str


class RobustnessTrial(ResponseModel):
    protocol_id: str
    name: str
    development_hash: str
    source_hash: str
    context_hash: str


class RobustnessReport(ResponseModel):
    id: str
    created_at: str
    request: RobustnessInput
    protocol: LabSummary
    config: SimulationConfig
    metrics: list[LabMetric]
    rejected: int
    expired: int
    trials: list[RobustnessTrial]
    snapshot_hash: str
    result: RobustnessResult
    python_version: str
    platform: str
    report_hash: str


class RobustnessHistory(ResponseModel):
    items: list[RobustnessReport]
    offset: int
    limit: int


class RobustnessReproduction(ResponseModel):
    id: str
    matches: bool
    result_matches: bool
    snapshot_matches: bool
    environment_matches: bool
    warnings: list[str]
