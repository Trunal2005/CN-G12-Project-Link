from typing import Literal, Any
import json
from pydantic import BaseModel, Field, ConfigDict, field_validator

class SessionCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    asset_id: Literal['calibration'] = 'calibration'
    policy: Literal['historical', 'ml', 'default'] = 'historical'
    profile: Literal['stable', 'step', 'gradual', 'fluctuate', 'unfamiliar'] = 'stable'
    seed: int = Field(default=42, ge=0, le=1000000)
    scale: float = Field(default=1, ge=.2, le=3, allow_inf_nan=False)
    purpose: Literal['explore', 'train', 'validation', 'test', 'smoke', 'calibration'] = 'explore'
    benchmark: bool = False
    duration_limit_s: int | None = Field(default=None,ge=5,le=600)

class Event(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    kind: Literal['intent','playing','waiting','pause','seeking','seeked','ended','error','sample','segment','decision','requested','rendered','interaction','configuration','request','close','excluded']
    seq: int | None = Field(default=None,ge=0)
    epoch: int = Field(default=0,ge=0)
    decision_id: str | None = Field(default=None,max_length=100)
    asset: str | None = Field(default=None,max_length=100)
    stream_type: str | None = Field(default=None,max_length=30)
    request_type: str | None = Field(default=None,max_length=50)
    media_time: float | None = Field(default=None,ge=0)
    decoded_frames: int | None = Field(default=None,ge=0)
    controller_version: str | None = Field(default=None,max_length=100)
    retry_attempts: int | None = Field(default=None,ge=0)
    rule_calls: int | None = Field(default=None,ge=0)
    t: float = Field(ge=0, le=86400)
    value: float | None = None
    buffer: float | None = Field(default=None, ge=0)
    throughput: float | None = Field(default=None, ge=0)
    duration: float | None = Field(default=None, ge=0)
    size: int | None = Field(default=None, ge=0)
    start: float | None = Field(default=None, ge=0)
    first_byte: float | None = Field(default=None, ge=0)
    media_start: float | None = None
    media_duration: float | None = Field(default=None, ge=0)
    representation: str | None = Field(default=None, max_length=100)
    request_id: str | None = Field(default=None, max_length=200)
    boundary: int | None = Field(default=None, ge=0)
    predictor: str | None = Field(default=None, max_length=80)
    reason: str | None = Field(default=None, max_length=500)
    features: list[float] | None = Field(default=None, max_length=20)
    inference_ms: float | None = Field(default=None, ge=0)
    timing_source: str | None = Field(default=None, max_length=80)
    settings: dict[str,Any] | None = None
    model_checksum: str | None = Field(default=None, pattern=r'^[0-9a-f]{64}$')

    @field_validator('settings')
    @classmethod
    def bounded_finite_settings(cls,value):
        if value is not None and len(json.dumps(value,allow_nan=False))>32000:raise ValueError('Configuration too large')
        return value

class Batch(BaseModel):
    events: list[Event] = Field(max_length=500)

class Finish(BaseModel):
    status: Literal['finished','cancelled','failed','partial'] = 'finished'
