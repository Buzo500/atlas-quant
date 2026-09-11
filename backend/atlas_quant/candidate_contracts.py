"""Append-only research decisions. No state represents permission to trade."""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from .contracts import ResponseModel
from .lab_contracts import LabSummary, LabMetric
from .simulation_contracts import SimulationConfig

CANDIDATE_POLICY = 'atlas-candidate-research-v1'
Status = Literal['researching', 'watchlist', 'discarded']
Hash = Annotated[str, Field(pattern=r'^[0-9a-f]{64}$')]


class CandidateInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, str_strip_whitespace=True)
    name: str = Field(min_length=3, max_length=100)
    hypothesis: str = Field(min_length=10, max_length=2000)
    reason: str = Field(min_length=10, max_length=2000)
    status: Status = 'researching'
    protocol_ids: list[Hash] = Field(default_factory=list, max_length=20)

    @field_validator('protocol_ids')
    @classmethod
    def distinct(cls, value):
        if len(set(value)) != len(value):
            raise ValueError('No repitas protocolos.')
        return sorted(value)


class CandidateRevisionInput(CandidateInput):
    expected_revision: int = Field(ge=1, le=99)


class CandidateEvidence(ResponseModel):
    protocol: LabSummary
    captured_at: str
    development_hash: str
    development_metrics: list[LabMetric]
    walk_forward_hash: str | None
    sensitivity_hash: str | None
    holdout_hash: str | None
    holdout_metrics: list[LabMetric] | None


class CandidateRevision(ResponseModel):
    id: str
    candidate_id: str
    revision: int
    name: str
    hypothesis: str
    reason: str
    status: Status
    created_at: str
    policy: Literal['atlas-candidate-research-v1']
    protocol_ids: list[str]
    evidence: list[CandidateEvidence]
    revision_hash: str


class CandidateSummary(ResponseModel):
    id: str
    name: str
    revision: int
    status: Status
    updated_at: str
    protocols: int


class CandidateHistory(ResponseModel):
    items: list[CandidateSummary]
    offset: int
    limit: int


class CandidateRevisions(ResponseModel):
    items: list[CandidateRevision]
    offset: int
    limit: int


class CandidateRef(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    candidate_id: Hash
    revision: int = Field(ge=1, le=100)


class CandidateComparisonInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    items: list[CandidateRef] = Field(min_length=2, max_length=4)

    @field_validator('items')
    @classmethod
    def distinct(cls, value):
        if len({(r.candidate_id, r.revision) for r in value}) != len(value):
            raise ValueError('No repitas la misma revisión.')
        return value


class CandidateComparisonContext(ResponseModel):
    revision_id: str
    protocol_id: str
    context_hash: str
    config: SimulationConfig


class CandidateComparison(ResponseModel):
    items: list[CandidateRevision]
    contexts: list[CandidateComparisonContext]
    same_context: bool
    warnings: list[str]
    comparison_hash: str
