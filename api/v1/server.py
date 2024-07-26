import sqlite3
from fastapi import FastAPI,APIRouter
from routers.posts import posts
from routers.users import users
from routers.auth import auth
from routers.votes import votes
from fastapi.middleware.cors import CORSMiddleware
from config import env

with sqlite3.connect('social_media_api.db') as db:
    cur=db.cursor()
    with open('./init.sql','r') as file:
        #turn on foreign keys
        cur.execute('PRAGMA foreign_keys = ON;')
        #init db
        cur.executescript(file.read())
        db.commit()

app=FastAPI()

#dealing with CORS

origins = [
    "http://localhost",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#building prefix router for versioning
prefix_router=APIRouter(prefix=f"/api/v{env.API_VERSION}")

#adding routers
prefix_router.include_router(posts.router)
prefix_router.include_router(users.router)
prefix_router.include_router(auth.router)
prefix_router.include_router(votes.router)

@prefix_router.get('/')
def root():
    return 'root'

#adding said prefix router
app.include_router(prefix_router)