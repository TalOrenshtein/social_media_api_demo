import sqlite3
from fastapi import APIRouter,status,HTTPException,Depends
from . import schemas
from typing import List,Optional
from utils import schemaKeysToStr,getAPIs_rowFactory
from ..auth import oauth2,schemas as authSchemas
from ..users import schemas as usersSchemas

with sqlite3.connect('social_media_api.db', check_same_thread=False) as db:
    #set up cursor
    cur=db.cursor()
    #turn on foreign keys
    cur.execute('PRAGMA foreign_keys = ON;')
    #set up row factory so SQL will return the results as a dict.
    cur.row_factory=getAPIs_rowFactory()
    #set up router
    router=APIRouter(prefix='/posts',tags=['Posts']) 

    @router.get('/',response_model=schemas.base_response)
    def get_posts(current_user:str=Depends(oauth2.get_current_user),
    page_size:int=10,page:int=1,search:Optional[str]="",sort_by:Optional[str]="ID",sort:Optional[str]="DESC"):
        r'''
        returning all post based on query parameters
        :returns: A base_response scheme serialization with posts_out scheme serialization as data.
        '''
        MAX_PAGE_SIZE=100
        if page<1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail='page argument must be greater than 0')
        if page_size<1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail=f'page_size argument must be between 1 and {MAX_PAGE_SIZE}')
        page_size=min(page_size,MAX_PAGE_SIZE)
        sqlArgs=[]
        #sort_by handle:
        sort_by=sort_by.lower()
        if sort_by not in [e.lower() for e in schemaKeysToStr(schemas.posts_out)]:
            #invalid sort, ignoring
            sort_by="ID"
        
        #sort handle:
        sort=sort.upper()
        if sort!='ASC': sort='DESC'

        # search arg handle:
        # setting sql query args so it'll include the search query only if exists.
        if search!="":
            # adding the query twice to search it twice, once at title and once at content.
            sqlArgs.extend([f"%{search}%",f"%{search}%"])
        
        #pagination handle:
        sqlArgs.extend([page_size,(page-1)*page_size])

        # posts table contains the ownerID but not the username, so,after querying the relevant data we'll be joining tables to find the username too
        # generalizing the idea that posts_out needs some info from users table that's not in posts table.
        extraInfo_from_userTable=[]
        for e in schemaKeysToStr(schemas.posts_out):
            if e not in schemas.get_posts_sql_columns() and e in schemaKeysToStr(usersSchemas.users_out):
                extraInfo_from_userTable.append(e)
        if len(extraInfo_from_userTable)>0:
            cur.execute(f'''--sql
            WITH posts_out AS
            (SELECT * FROM posts
            {"WHERE (title LIKE ? OR content LIKE ?)" if search!="" else " "}),
            count_votes AS (SELECT * FROM votes),
            user_table AS 
            (SELECT ID{f',{",".join(extraInfo_from_userTable)}' if len(extraInfo_from_userTable)>0 else ""} --fetching extra fields if needed.
            FROM users WHERE ID in (select ownerID from posts_out)), --this where clause should,in theory, redude the size of the join table by reducing the size of one of the joined tables by filtering unnecessary rows before the join action.
            posts_and_users AS (SELECT posts_out.*
            {f',user_table.{",user_table.".join(extraInfo_from_userTable)}' if len(extraInfo_from_userTable)>0 else ""}
            FROM user_table CROSS JOIN posts_out ON posts_out.ownerID=user_table.ID)
            SELECT posts_and_users.*,COUNT(votes.postID) as votes FROM posts_and_users LEFT JOIN votes ON votes.postID=posts_and_users.ID GROUP BY posts_and_users.ID
            ORDER BY {sort_by} {sort},created_at DESC --impossive to sql inject these as each is a chosen value from a fixed sized pool of values.
            LIMIT ? OFFSET ?
            ''',sqlArgs)

        else:
            cur.execute(f'''--sql
            WITH posts_out as (SELECT * FROM posts
            {"WHERE (title LIKE ? OR content LIKE ?)" if search!="" else " "})
            SELECT posts_out.*,COUNT(votes.postID) as votes FROM posts_out LEFT JOIN votes ON votes.postID=posts_out.ID GROUP BY posts_out.ID
            ORDER BY {sort_by} {sort}, posts_out.created_at DESC --impossive to sql inject these as each is a chosen value from a fixed sized pool of values.
            LIMIT ? OFFSET ?
            ''',sqlArgs)

        posts=cur.fetchall()
        return {
            "page":page,
            "page_size":page_size,
            "data":[schemas.posts_out(**post) for post in posts] #creating list of posts_out so the response model can serialize
            }

    @router.get('/{id}',response_model=schemas.posts_out)
    def get_post(id:int,current_user:str=Depends(oauth2.get_current_user)):
        # posts table contains the ownerID but not the username, so,after querying the relevant data we'll be joining tables to find the username too
        # generalizing the idea that posts_out needs some info from users table that's not in posts table.
        extraInfo_from_userTable=[]
        for e in schemaKeysToStr(schemas.posts_out):
            if e not in schemas.get_posts_sql_columns() and e in schemaKeysToStr(usersSchemas.users_out):
                extraInfo_from_userTable.append(e)
        if len(extraInfo_from_userTable)>0:
            cur.execute(f'''--sql
            WITH posts_out AS (SELECT * FROM posts WHERE ID=?),
            count_votes AS (SELECT COUNT(postID) AS votes FROM votes where postID=?),
            user_table AS (SELECT ID{f',{",".join(extraInfo_from_userTable)}' if len(extraInfo_from_userTable)>0 else ""} FROM users)
            SELECT posts_out.*
            {f',user_table.{",user_table.".join(extraInfo_from_userTable)}' if len(extraInfo_from_userTable)>0 else ""}
            ,count_votes.*
            FROM user_table CROSS JOIN posts_out ON posts_out.ownerID=user_table.ID,count_votes
            ''',[int(id),int(id)])
        else:
            cur.execute('''--sql
            WITH count_votes AS (SELECT COUNT(postID) AS votes FROM votes where postID=?)
            SELECT * FROM posts,count_votes WHERE posts.ID=?
            ''',[int(id),int(id)])

        post=cur.fetchone()
        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"post with id {id} doesn't exist.")
        return post
    
    @router.post('/',response_model=schemas.posts_out,status_code=status.HTTP_201_CREATED)
    def create_post(post: schemas.posts_in,current_user:authSchemas.TokenData=Depends(oauth2.get_current_user)):
        post=schemas.posts_in(**post.dict())
        if post.content=="" and post.title=="":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="post title and content cannot be empty at the same time.")
        cur.execute(f'INSERT INTO posts(ownerID,{",".join(schemaKeysToStr(schemas.posts_in))}) VALUES(?,?,?)',[current_user.ID,post.title,post.content])
        db.commit()

        # posts table contains the ownerID but not the username, so,after querying the relevant data we'll be joining tables to find the username too
        # generalizing the idea that posts_out needs some info from users table that's not in posts table.
        extraInfo_from_userTable=[]
        for e in schemaKeysToStr(schemas.posts_out):
            if e not in schemas.get_posts_sql_columns() and e in schemaKeysToStr(usersSchemas.users_out):
                extraInfo_from_userTable.append(e)
        if len(extraInfo_from_userTable)>0:
            cur.execute(f'''--sql
            WITH post_created AS (SELECT * FROM posts WHERE ID=?),
            user_table AS (SELECT ID{f',{",".join(extraInfo_from_userTable)}' if len(extraInfo_from_userTable)>0 else ""} FROM users)
            SELECT post_created.* {f',user_table.{",user_table.".join(extraInfo_from_userTable)}' if len(extraInfo_from_userTable)>0 else ""}
            FROM user_table CROSS JOIN post_created --ON post_created.ownerID=user_table.ID
            ''',[cur.lastrowid])
        else:
            cur.execute('''--sql
            SELECT * FROM posts WHERE ID=?
            ''',[cur.lastrowid])
        post=cur.fetchone()
        return post

    @router.delete('/{id}',status_code=status.HTTP_204_NO_CONTENT)
    def delete_posts(id:int,current_user=Depends(oauth2.get_current_user)):
        r'''
            Deletes a post created by this user.
        '''
        cur.execute('DELETE FROM posts WHERE ownerID=? and ID=?',[current_user.ID,int(id)])
        if cur.rowcount==0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        db.commit()

    @router.delete('/',status_code=status.HTTP_204_NO_CONTENT)
    def delete_posts(current_user=Depends(oauth2.get_current_user)):
        r'''
            Deletes this users' posts.
        '''
        cur.execute('DELETE FROM posts WHERE ownerID=?',[current_user.ID])
        if cur.rowcount==0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail='No posts exists.')
        db.commit()
    @router.delete('/ALL',status_code=status.HTTP_204_NO_CONTENT)
    def delete_all_posts():
        r'''
            Deletes all posts.
        '''
        cur.execute('DELETE FROM posts')
        db.commit()