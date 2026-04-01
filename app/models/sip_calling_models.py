
from pydantic import BaseModel
import uuid

class UserCalling(BaseModel):
    call_id:uuid.UUID
    username: str
    phone_number:int
    requested_phone_number:int
    role: str
    
class CheckCallStatus(BaseModel):
    call_status:str
    call_sid:str    