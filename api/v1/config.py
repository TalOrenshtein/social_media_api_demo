from pydantic_settings import BaseSettings,SettingsConfigDict

class Env(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')
    JWT_SECRET_KEY:str
    JWT_ALGORITHM:str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES:int=30
    API_VERSION:int=1
    EXPAND_MAX_DEPTH:int=4

env=Env()