import jwt
from datetime import datetime,timedelta,UTC
from jwt import InvalidTokenError
from . import schemas
from fastapi import Depends,status,HTTPException
from fastapi.security.oauth2 import OAuth2PasswordBearer
import sqlite3
from config import env

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
#JWT CONSTATNTS
SECRET_KEY = env.JWT_SECRET_KEY
ALGORITHM = env.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = env.JWT_ACCESS_TOKEN_EXPIRE_MINUTES

def create_token(data:dict, expires_timedelta:timedelta|None=None):
    to_encode=data.copy()
    expire=datetime.now(UTC)+(expires_timedelta if expires_timedelta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode,SECRET_KEY,algorithm=ALGORITHM)

def verify_token(token:str,credentials_exception):
    try:
        decoded=jwt.decode(token,SECRET_KEY,algorithms=ALGORITHM)
        ID=decoded.get('ID')
        if ID is None:
            raise credentials_exception
        data=schemas.TokenData(ID=ID)
        return data
    except InvalidTokenError as e:
        raise credentials_exception from e

def get_current_user(token:str=Depends(oauth2_scheme)):
    credentials_exception=HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate":"Bearer"}
    )
    verified_data=verify_token(token,credentials_exception)
    #search the db if user is still registered and continue only if he is.
    with sqlite3.connect('social_media_api.db', check_same_thread=False) as db:
        #set up cursor
        cur=db.cursor()
        #turn on foreign keys
        #cur.execute('PRAGMA foreign_keys = ON;')
        
        cur.execute('''--sql
        SELECT ID FROM users WHERE ID=?
        ''',[verified_data.ID])
        if not cur.fetchone():
            raise credentials_exception
    return verified_data