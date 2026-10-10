import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid')


class SamplePair(Contract):
    stdin: str = Field(min_length=1, max_length=100000)
    stdout: str = Field(min_length=1, max_length=65536)

    @field_validator('stdin', 'stdout')
    @classmethod
    def nonempty(cls, value):
        if not value.strip():
            raise ValueError('Sample fields must be nonempty')
        return value


class ProblemInput(Contract):
    title: str = Field(default='', max_length=300)
    statement: str = Field(min_length=1, max_length=100000)
    samples: list[SamplePair] = Field(default_factory=list, max_length=32)
    warnings: list[str] = Field(default_factory=list, max_length=32)

    @field_validator('statement')
    @classmethod
    def nonempty(cls, value):
        if not value.strip():
            raise ValueError('Statement must be nonempty')
        return value


class RunRequest(Contract):
    problem: ProblemInput
    source: str = Field(min_length=1, max_length=262144)
    seed: int = Field(default=850, ge=0, le=2**32 - 1)

    @field_validator('source')
    @classmethod
    def source_size(cls, value):
        if not value.strip() or len(value.encode()) > 262144:
            raise ValueError('Source must be nonempty and at most 256 KiB')
        return value

    @model_validator(mode='after')
    def complete_samples(self):
        if not self.problem.samples:
            raise ValueError('At least one complete sample is required')
        from app.outputs import integer_tokens
        for sample in self.problem.samples:
            integer_tokens(sample.stdout)
        return self


class GeneratedBundle(Contract):
    code: str = Field(min_length=1, max_length=262144)
    method: str = Field(min_length=1, max_length=2000)
    small_input_limits: str = Field(min_length=1, max_length=1000)

    @field_validator('code', 'method', 'small_input_limits')
    @classmethod
    def nonempty(cls, value):
        if not value.strip() or len(value.encode()) > 262144:
            raise ValueError('Generated fields must be nonempty and bounded')
        return value


class ConfirmationBundle(Contract):
    code: str = Field(min_length=1, max_length=262144)
    method: str = Field(min_length=1, max_length=2000)

    @field_validator('code', 'method')
    @classmethod
    def nonempty(cls, value):
        if not value.strip() or len(value.encode()) > 262144:
            raise ValueError('Confirmation fields must be nonempty and bounded')
        return value


class WorkerReply(Contract):
    value: JsonValue = None
    cases: list[JsonValue] = Field(default_factory=list, max_length=64)

    @model_validator(mode='after')
    def bounded_json(self):
        try:
            data = json.dumps(self.model_dump(), allow_nan=False)
        except (ValueError, RecursionError) as error:
            raise ValueError('Worker values must be finite JSON') from error
        if len(data.encode()) > 48000:
            raise ValueError('Worker payload exceeds limit')
        return self


class ExecutionResult(BaseModel):
    model_config = ConfigDict(extra='forbid')

    status: Literal['ok', 'runtime_error', 'timeout', 'output_limit', 'runner_error', 'cancelled']
    stdout: str = ''
    stderr: str = ''
    exit_code: int | None = None
    elapsed: float = Field(default=0, ge=0)


class Counts(Contract):
    generated: int = Field(default=0, ge=0)
    valid: int = Field(default=0, ge=0)
    tested: int = Field(default=0, ge=0)
    invalid: int = Field(default=0, ge=0)
    timed_out: int = Field(default=0, ge=0)


class Evidence(Contract):
    stdin: str
    expected: str
    actual: ExecutionResult
    confirmation: str | None = None
    references_agree: bool = False
    validators_agree: bool = False
    samples_checked: bool = False
    primary_code: str = ''
    confirmation_code: str = ''
    candidate_hash: str = ''
    primary_hash: str = ''
    confirmation_hash: str = ''


class CounterexampleResult(Contract):
    outcome: Literal['corroborated_counterexample', 'unconfirmed_disagreement', 'inconclusive', 'runtime_finding', 'preparation_failure', 'provider_failure', 'runner_failure', 'cancelled']
    message: str
    evidence: Evidence | None = None
    seed: int = 850
    counts: Counts = Field(default_factory=Counts)
    elapsed: float = Field(default=0, ge=0)
    method: str = ''
    explanation: str = ''
    explanation_ai_generated: bool = False

    @model_validator(mode='after')
    def confirmed_requires_evidence(self):
        if self.outcome == 'corroborated_counterexample':
            evidence = self.evidence
            if not evidence or not evidence.references_agree or not evidence.validators_agree or not evidence.samples_checked or evidence.confirmation is None or evidence.actual.status != "ok":
                raise ValueError('Corroboration requires executed evidence')
            from app.outputs import integer_tokens
            if integer_tokens(evidence.expected) != integer_tokens(evidence.confirmation):
                raise ValueError('References must agree')
            try:
                agrees = integer_tokens(evidence.expected) == integer_tokens(evidence.actual.stdout)
            except ValueError:
                agrees = False
            if agrees:
                raise ValueError('Candidate must disagree')
        return self


class RunSnapshot(Contract):
    id: str
    stage: str = 'queued'
    elapsed: float = 0
    counts: Counts = Field(default_factory=Counts)
    terminal: bool = False
    result: CounterexampleResult | None = None
