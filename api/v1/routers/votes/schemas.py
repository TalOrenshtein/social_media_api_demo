from pydantic import BaseModel,Field

class vote_in(BaseModel):
    post:str

class vote_out(BaseModel):
    post:str
    user:str