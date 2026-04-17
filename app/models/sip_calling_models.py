from pydantic import BaseModel
import uuid

class UserCalling(BaseModel):
    customer_name: str
    call_type: str
    caller_name: str
    call_date: str
    customer_number: str
    call_sid: str
    
    
class CheckCallStatus(BaseModel):
    call_status:str
    call_sid:str    

class CallRecording(BaseModel):
    call_sid: str    