from pydantic import BaseModel as _PydanticBaseModel
from pydantic import ConfigDict

try:
    from lionagi.models import HashableModel as _LionHashableModel
except Exception:  # pragma: no cover - allow offline/test without lionagi
    _LionHashableModel = _PydanticBaseModel

__all__ = ("BaseModel",)


class BaseModel(_LionHashableModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra="forbid",
        use_enum_values=True,
        populate_by_name=True,
    )
