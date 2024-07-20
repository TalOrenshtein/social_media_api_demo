from fastapi import APIRouter,HTTPException,status
from . import schemas
from utils import hashPW,schemaKeysToStr,getAPIs_rowFactory,verifyPW
import sqlite3
from . import oauth2



with sqlite3.connect('social_media_api.db', check_same_thread=False) as db:
    #set up cursor
    cur=db.cursor()
    #turn on foreign keys
    cur.execute('PRAGMA foreign_keys = ON;')
    #set up router
    router=APIRouter(tags=['Authentication'],prefix='/login')

    @router.post('/')
    def login(login_attempt: schemas.UserLogin):
        login_attempt=schemas.UserLogin(**login_attempt.dict())
        cur.row_factory=getAPIs_rowFactory()
        cur.execute(f'SELECT ID,{','.join(schemaKeysToStr(schemas.UserLogin))} FROM users WHERE username=?',[login_attempt.username])
        user=cur.fetchone()
        if not user or not verifyPW(login_attempt.password,user['password']):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Invalid Credentials")
        return {'token':oauth2.create_token({"ID":user['ID'],"token_type":"bearer"}),'token_type':"bearer"}

