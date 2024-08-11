from pydantic_settings import BaseSettings,SettingsConfigDict

class Env(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')
    JWT_SECRET_KEY:str
    JWT_ALGORITHM:str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES:int=30
    API_VERSION:int=1
    EXPAND_MAX_DEPTH:int=4
    DB_USERNAME:str
    DB_PASSWPRD:str
    DB_HOSTNAME:str
    DB_PORT:int=5432
    DB_NAME:str="social_media_api"
    DB_MIN_CONNS:int=1
    DB_MAX_CONNS:int=10

env=Env()