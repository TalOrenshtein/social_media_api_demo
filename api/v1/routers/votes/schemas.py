from pydantic import BaseModel,Field

class vote_in(BaseModel):
    postID:str

class vote_out(BaseModel):
    postID:str
    userID:str