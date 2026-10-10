from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ExecutionResult(BaseModel):
    model_config = ConfigDict(extra='forbid')

    status: Literal['ok', 'runtime_error', 'timeout', 'output_limit', 'runner_error', 'cancelled']
    stdout: str = ''
    stderr: str = ''
    exit_code: int | None = None
    elapsed: float = Field(default=0, ge=0)
