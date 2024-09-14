from fastapi import APIRouter,status,HTTPException,Depends,Query
from . import schemas
from utils import schemaKeysToStr,getAPIs_rowFactory,handle_expand
from typing import List,Optional
from ..auth import oauth2,schemas as authSchemas
from db import db_pool


#set up router
router=APIRouter(prefix='/votes',tags=['Votes']) 

@router.get('/',response_model=List[schemas.vote_out])
def get_votes():
    cur.execute('SELECT * FROM votes')
    votes=cur.fetchall()
    return votes

@router.get('/{id}',response_model=schemas.vote_out)#List[schemas.vote_out])
def get_vote(id,expand:Optional[List[str]]=Query(None,alias='expand[]')):
    #I know it's weird to implement this, but it's here just for demonstrating the expand feature
    post,user=id.split("&")
    cur.execute('SELECT * FROM votes WHERE post=%s AND user=%s',(post,user,))
    vote=cur.fetchone()
    if expand:
        vote=handle_expand(expand,vote,schemas.vote_out,"votes")
    return vote

@router.post('/',response_model=schemas.vote_out,status_code=201)
def create_vote(vote:schemas.vote_in,current_user:authSchemas.TokenData=Depends(oauth2.get_current_user)):
    with db_pool.connection() as con:
        cur=con.cursor()
        cur.execute('''--sql
        SELECT ID FROM posts WHERE ID=%s
        ''',(vote.post,))
        if not cur.fetchone():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"post with id {vote.post} doesn't exist.")
        cur.execute('SELECT * FROM votes WHERE postid=%s AND userid=%s',(vote.post,current_user.ID))
        current_vote=cur.fetchone()
        if not current_vote:
            cur.execute('''--sql
                INSERT INTO votes VALUES(%s,%s) 
            ''',(vote.post,current_user.ID))
            cur.execute('''--sql
                SELECT * FROM votes WHERE postid=%s AND userid=%s
            ''',(vote.post,current_user.ID))
            vote=cur.fetchone()
            return vote
        else:
            cur.execute('''--sql
                DELETE FROM votes WHERE postid=%s AND userid=%s
            ''',(vote.post,current_user.ID))
            raise HTTPException(status_code=status.HTTP_204_NO_CONTENT)