import sqlite3
from fastapi import APIRouter,status,HTTPException,Depends
from . import schemas
from utils import schemaKeysToStr,getAPIs_rowFactory
from typing import List
from ..auth import oauth2,schemas as authSchemas

with sqlite3.connect('social_media_api.db', check_same_thread=False) as db:
    #set up cursor
    cur=db.cursor()
    #turn on foreign keys
    cur.execute('PRAGMA foreign_keys = ON;')
    #set up row factory so SQL will return the results as a dict.
    cur.row_factory=getAPIs_rowFactory()
    #set up router
    router=APIRouter(prefix='/votes',tags=['Votes']) 

    @router.get('/',response_model=List[schemas.vote_out])
    def get_votes():
        cur.execute('SELECT * FROM votes')
        votes=cur.fetchall()
        return votes
    
    @router.get('/{id}',response_model=List[schemas.vote_out])
    def get_vote():
        #TODO
        cur.execute('SELECT * FROM votes WHERE X=?',[id])
        vote=cur.fetchone()
        return vote

    @router.post('/',response_model=schemas.vote_out,status_code=201)
    def create_vote(vote:schemas.vote_in,current_user:authSchemas.TokenData=Depends(oauth2.get_current_user)):
        cur.execute('''--sql
        SELECT ID FROM posts WHERE ID=?
        ''',[vote.postID])
        if not cur.fetchone():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"post with id {vote.postID} doesn't exist.")
        cur.execute('SELECT * FROM votes WHERE postID=? AND userID=?',[vote.postID,current_user.ID])
        current_vote=cur.fetchone()
        if not current_vote:
            cur.execute('''--sql
                INSERT INTO votes VALUES(?,?) 
            ''',[vote.postID,current_user.ID])
            db.commit()
            cur.execute('''--sql
                SELECT * FROM votes WHERE postID=? AND userID=?
            ''',[vote.postID,current_user.ID])
            vote=cur.fetchone()
            return vote
        else:
            cur.execute('''--sql
                DELETE FROM votes WHERE postID=? AND userID=?
            ''',[vote.postID,current_user.ID])
            db.commit()
            raise HTTPException(status_code=status.HTTP_204_NO_CONTENT)