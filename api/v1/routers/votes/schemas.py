from pydantic import BaseModel,Field,SerializeAsAny
from ..posts.schemas import posts_out
from ..users.schemas import users_out

class vote_in(BaseModel):
    post:str

class vote_out(BaseModel):
    postid:str | SerializeAsAny[posts_out]
    userid:str | SerializeAsAny[users_out]