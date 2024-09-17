from pydantic import BaseModel,Field,SerializeAsAny
from datetime import datetime
from typing import List,Annotated#,Optional
from utils import get_sql_schema
from ..users.schemas import users_out

class posts_in(BaseModel):
    title:str=Field(default='')
    content:str=Field(default='')

class posts_out(BaseModel):
    id:str
    user:str|SerializeAsAny[users_out]
    username:Annotated[str,Field(description='user')] #Optional field. By convention, the field's description will hold the name of the external object that said field depend on, represented as a single resource.
    # email:Annotated[str,Field(description='user')] #Optional field. By convention, the field's description will hold the name of the external object that said field depend on, represented as a single resource.
    title:str
    content:str
    votes:int=Field(default=0) #This field is mandatory as we wil ALWAYS want to see the votes as an integral part of the post. Votes are hard coded within the posts endpoints; removing it will break things.
    created_at:datetime

class base_response(BaseModel):
    page:int
    page_size:int
    is_last_page:bool=Field(default=True)
    data:SerializeAsAny[List[BaseModel]] #making sure polymorphism works

def get_posts_sql_schema()->dict:
    r'''
    get a dict with the columns as keys and their types as values
    :returns: a dict with the columns as keys and their types as values
    '''
    return get_sql_schema('posts')

def get_posts_sql_columns()->list:
    r'''
    get a list of posts' columns names
    :returns: a list of posts' columns names
    '''
    return [key for key in get_posts_sql_schema()]