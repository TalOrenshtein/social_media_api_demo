from pydantic import BaseModel

class UserLogin(BaseModel):
    username:str
    password:str

class Token(BaseModel):
    token:str
    token_type:str

class TokenData(BaseModel):
    ID:str