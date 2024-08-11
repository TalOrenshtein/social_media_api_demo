from uuid import uuid4
from fastapi import APIRouter,status,HTTPException,Depends,Query
from . import schemas
from typing import List,Optional
from utils import schemaKeysToStr,getAPIs_rowFactory,hashPW,handle_expand
from ..auth import oauth2
from db import db_pool

#set up router
router=APIRouter(prefix='/users',tags=['Users'])


@router.get('/',response_model=List[schemas.users_out])
def get_users(current_user:str=Depends(oauth2.get_current_user)):
    r'''
    Return all existing users.
    '''
    with db_pool.connection() as con:
        cur=con.cursor()
        cur.execute(f'SELECT {",".join(schemaKeysToStr(schemas.users_out))} FROM users;')
        return cur.fetchall()

@router.get('/{id}',response_model=schemas.users_out)
def get_user(id,current_user:str=Depends(oauth2.get_current_user),expand:Optional[List[str]]=Query(None,alias='expand[]')):
    r'''
    Searching and returning a used with {id} ID
    '''
    with db_pool.connection() as con:
        cur=con.cursor()
        cur.execute(f'SELECT {",".join(schemaKeysToStr(schemas.users_out))} FROM users WHERE ID=?',(id,))
        user=cur.fetchone()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"user with id {id} doesn't exist.")
        if expand:
            user=handle_expand(expand,user,schemas.users_out,"users")
        return user

@router.post('/',response_model=schemas.users_out,status_code=status.HTTP_201_CREATED)
def create_user(user: schemas.users_in):
    r'''
        Creates a user.
    '''
    user=schemas.users_in(**user.dict())
    user.password=hashPW(user.password)
    uuid=None
    with db_pool.connection() as con:
        #searching for available uuid
        cur=con.cursor()
        while True:
            uuid=f"u_{uuid4().hex}"
            cur.execute('SELECT ID FROM users WHERE ID=%s;',(uuid,))
            if cur.fetchone() is None:
                break
        #trying to create a user
        cur.execute(f'INSERT INTO users (ID,{",".join(schemaKeysToStr(schemas.users_in))}) VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING;'
        ,(uuid,user.username,user.email,user.password))
        if cur.rowcount<1:
            #confict found
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,detail=f"email '{user.email}' or username '{user.username}' already registered.")
        #getting the just-created user to return its' details as a result
        cur.execute(f'SELECT {",".join(schemaKeysToStr(schemas.users_out))} FROM users WHERE ID=%s;',(uuid,))
        #user=db.sql_exec(f'SELECT {",".join(schemaKeysToStr(schemas.users_out))} FROM users WHERE ID=%s;',(uuid,))
        user=cur.fetchone()
        return user

@router.delete('/',status_code=status.HTTP_204_NO_CONTENT)
def delete_user(current_user=Depends(oauth2.get_current_user)):
    r'''
        Delete this users.
    '''
    with db_pool.connection() as con:
        con.execute('DELETE FROM users WHERE ID=%s;',(current_user.ID,))

@router.delete('/ALL',status_code=status.HTTP_204_NO_CONTENT)
def delete_users():
    r'''
        Delete all users.
    '''
    with db_pool.connection() as con:
        con.execute('DELETE FROM users;')