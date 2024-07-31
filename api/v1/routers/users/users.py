import sqlite3
from uuid import uuid4
from fastapi import APIRouter,status,HTTPException,Depends,Query
from . import schemas
from typing import List,Optional
from utils import schemaKeysToStr,getAPIs_rowFactory,hashPW,handle_expand
from ..auth import oauth2


with sqlite3.connect('social_media_api.db', check_same_thread=False) as db:
    #set up cursor
    cur=db.cursor()
    #turn on foreign keys
    cur.execute('PRAGMA foreign_keys = ON;')
    #set up row factory so SQL will return the results as a dict.
    cur.row_factory=getAPIs_rowFactory()
    #set up router
    router=APIRouter(prefix='/users',tags=['Users'])


    @router.get('/',response_model=List[schemas.users_out])
    def get_users(current_user:str=Depends(oauth2.get_current_user)):
        r'''
        Return all existing users.
        '''
        cur.execute(f'SELECT {",".join(schemaKeysToStr(schemas.users_out))} FROM users')
        users=cur.fetchall()
        return users

    @router.get('/{id}',response_model=schemas.users_out)
    def get_user(id,current_user:str=Depends(oauth2.get_current_user),expand:Optional[List[str]]=Query(None,alias='expand[]')):
        r'''
        Searching and returning a used with {id} ID
        '''
        cur.execute(f'SELECT {",".join(schemaKeysToStr(schemas.users_out))} FROM users WHERE ID=?',[id])
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
        #searching for available uuid
        while True:
            uuid=f"u_{uuid4().hex}"
            cur.execute('SELECT ID FROM users WHERE ID=?',[uuid])
            if cur.fetchone() is None:
                break
        cur.execute(f'INSERT OR IGNORE INTO users (ID,{",".join(schemaKeysToStr(schemas.users_in))}) VALUES(?,?,?,?)',[uuid,user.username,user.email,user.password])
        db.commit()
        if cur.lastrowid<1:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,detail=f"email '{user.email}' or username '{user.username}' already registered.")
        cur.execute(f'SELECT {",".join(schemaKeysToStr(schemas.users_out))} FROM users WHERE ID=?',[uuid])
        user=cur.fetchone()
        return user

    @router.delete('/',status_code=status.HTTP_204_NO_CONTENT)
    def delete_user(current_user=Depends(oauth2.get_current_user)):
        r'''
            Deletes this users.
        '''
        cur.execute('DELETE FROM users WHERE ID=?',[current_user.ID])
        db.commit()
    @router.delete('/ALL',status_code=status.HTTP_204_NO_CONTENT)
    def delete_users():
        r'''
            Deletes all users.
        '''
        cur.execute('DELETE FROM users')
        db.commit()
