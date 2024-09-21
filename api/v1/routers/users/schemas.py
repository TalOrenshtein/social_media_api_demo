from pydantic import BaseModel,EmailStr
from datetime import datetime
#from typing import Optional

class users_in(BaseModel):
    username: str
    email: EmailStr
    password: str
    
class users_out(BaseModel):
    id: str
    username: str
    email: EmailStr
    created_at: datetime