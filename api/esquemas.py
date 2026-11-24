from typing import Literal, Annotated

from pydantic import BaseModel, ConfigDict, Field

Positive = Annotated[float, Field(gt=0, allow_inf_nan=False)]


class Reading(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    product_type: Literal["L", "M", "H"]
    air_temperature_k: Positive
    process_temperature_k: Positive
    rotational_speed_rpm: Positive
    torque_nm: Positive
    tool_wear_min: Annotated[float, Field(ge=0, allow_inf_nan=False)]
