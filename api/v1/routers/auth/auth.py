from fastapi import APIRouter,HTTPException,status
from . import schemas
from utils import hashPW,schemaKeysToStr,verifyPW
from . import oauth2
from db import db_pool

#set up router
router=APIRouter(tags=['Authentication'],prefix='/login')

@router.post('/')
def login(login_attempt: schemas.UserLogin):
    with db_pool.connection() as con:
        cur=con.cursor()
        login_attempt=schemas.UserLogin(**login_attempt.dict())
        cur.execute(f'SELECT ID,{','.join(schemaKeysToStr(schemas.UserLogin))} FROM users WHERE username=%s',(login_attempt.username,))
        user=cur.fetchone()
        if not user or not verifyPW(login_attempt.password,user['password']):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Invalid Credentials")
        return {'token':oauth2.create_token({"ID":user['id'],"token_type":"bearer"}),'token_type':"bearer"}

