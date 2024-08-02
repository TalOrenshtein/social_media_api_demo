from pydantic import BaseModel,Field,SerializeAsAny
from ..posts.schemas import posts_out
from ..users.schemas import users_out

class vote_in(BaseModel):
    post:str

class vote_out(BaseModel):
    post:str | SerializeAsAny[posts_out]
    user:str | SerializeAsAny[users_out]