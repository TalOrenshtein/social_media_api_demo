from pydantic import BaseModel,Field

class vote_in(BaseModel):
    postID:int

class vote_out(BaseModel):
    postID:int
    userID:str