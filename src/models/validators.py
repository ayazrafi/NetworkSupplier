from typing import Annotated, Any
from pydantic import BeforeValidator
from bson import ObjectId

def validate_object_id(v: Any) -> str:
    if isinstance(v, ObjectId):
        return str(v)
    if not isinstance(v, str):
        raise ValueError("Invalid ObjectId: must be a string or ObjectId instance")
    if not ObjectId.is_valid(v):
        raise ValueError("Invalid ObjectId: must be a 24-character hex string")
    return v

ObjectIdStr = Annotated[str, BeforeValidator(validate_object_id)]
