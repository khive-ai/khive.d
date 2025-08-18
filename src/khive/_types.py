from lionagi.models import HashableModel
from pydantic import ConfigDict

__all__ = ("BaseModel",)


class BaseModel(HashableModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra="forbid",
        use_enum_values=True,
        populate_by_name=True,
    )
