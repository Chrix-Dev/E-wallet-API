from pydantic import BaseModel, field_validator


class SetPinRequest(BaseModel):
    pin: str
    confirm_pin: str

    @field_validator("pin")
    def pin_must_be_4_digits(cls, v):
        if not v.isdigit() or len(v) != 4:
            raise ValueError("PIN must be exactly 4 digits")
        return v

    @field_validator("confirm_pin")
    def pins_must_match(cls, v, values):
        if "pin" in values.data and v != values.data["pin"]:
            raise ValueError("PINs do not match")
        return v


class ChangePinRequest(BaseModel):
    old_pin: str
    new_pin: str
    confirm_new_pin: str

    @field_validator("new_pin")
    def pin_must_be_4_digits(cls, v):
        if not v.isdigit() or len(v) != 4:
            raise ValueError("PIN must be exactly 4 digits")
        return v

    @field_validator("confirm_new_pin")
    def pins_must_match(cls, v, values):
        if "new_pin" in values.data and v != values.data["new_pin"]:
            raise ValueError("PINs do not match")
        return v