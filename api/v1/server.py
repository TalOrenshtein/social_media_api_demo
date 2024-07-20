import sqlite3
from fastapi import FastAPI
from routers.posts import posts
from routers.users import users
from routers.auth import auth
from routers.votes import votes
from fastapi.middleware.cors import CORSMiddleware

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

#adding routers
app.include_router(posts.router)
app.include_router(users.router)
app.include_router(auth.router)
app.include_router(votes.router)

@app.get('/')
def root():
    return 'root'