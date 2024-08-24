import sqlite3
from fastapi import APIRouter,status,HTTPException,Depends,Query
from . import schemas
from typing import List,Optional
from utils import schemaKeysToStr,getAPIs_rowFactory,handle_expand
from ..auth import oauth2,schemas as authSchemas
from ..users import schemas as usersSchemas
from uuid import uuid4

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

        # checking if posts_out schema needs some info from an external object (i.e username from user object).
        object_fields_mapping={} #holds object names as keys and list of values as value.
        for field,meta_data in schemas.posts_out.model_fields.items():
            if meta_data.description is not None:
                external_object=meta_data.description #by convention, the field's description will hold the name of the external object that said field depend on, represented as a single resource.
                if external_object not in object_fields_mapping:
                    object_fields_mapping[external_object]=[field]
                else:
                    object_fields_mapping[external_object].append(field)
        if object_fields_mapping!={}:
            sql_script=f'''--sql
                WITH posts_out AS
                (SELECT * FROM posts
                {"WHERE (title LIKE ? OR content LIKE ?)" if search!="" else " "}),
                count_votes AS (SELECT * FROM votes),
                --creating a table for each object that post's schema depends on, and will append them with the relevant fields to the with section to include them all.
                --assuming that the table name is a representation of a resource as a collection (i.e users and not user).
                {",".join([f'''{external_object}_table AS (SELECT ID{f',{",".join(external_fields)}'} --selecting all relevant fields and ID
                FROM {external_object}s WHERE ID in (select {external_object} from posts_out)), --this where clause should,in theory, redude the size of the join table by reducing the size of one of the joined tables by filtering unnecessary rows before the join action.'''
                for external_object,external_fields in object_fields_mapping.items()])}
                -- join all the tables we included with the WITH statement, with filtering on posts_out.<external_object>=<external_object>_table.ID
                {f'''posts_joined AS (SELECT posts_out.*{f'{','.join([f'''{f''',{external_object}_table.
                {f",{external_object}_table.".join(external_fields)}'''}
                ''' for external_object,external_fields in object_fields_mapping.items()])}'}
                FROM posts_out CROSS JOIN 
                {'CROSS JOIN '.join([f'''{external_object}_table ON posts_out.{external_object}={external_object}_table.ID'''
                for external_object,external_fields in object_fields_mapping.items()])} ) --closing the post_joined statement
                SELECT posts_joined.*,COUNT(votes.post) as votes FROM posts_joined LEFT JOIN votes ON votes.post=posts_joined.ID GROUP BY posts_joined.ID
                ORDER BY {sort_by} {sort},created_at DESC --impossive to sql inject these as each is a chosen value from a fixed sized pool of values.
                LIMIT ? OFFSET ?
                '''}
            '''
        else:
            sql_script=f'''--sql
            WITH posts_out as (SELECT * FROM posts
            {"WHERE (title LIKE ? OR content LIKE ?)" if search!="" else " "})
            SELECT posts_out.*,COUNT(votes.post) as votes FROM posts_out LEFT JOIN votes ON votes.post=posts_out.ID GROUP BY posts_out.ID
            ORDER BY {sort_by} {sort}, posts_out.created_at DESC --impossive to sql inject these as each is a chosen value from a fixed sized pool of values.
            LIMIT ? OFFSET ?
            '''
        cur.execute(sql_script,sqlArgs)
        posts=cur.fetchall()
        return {
            "page":page,
            "page_size":page_size,
            "data":[schemas.posts_out(**post) for post in posts] #creating list of posts_out so the response model can serialize
            }

    @router.get('/{id}',response_model=schemas.posts_out)
    def get_post(id:str,current_user:str=Depends(oauth2.get_current_user),expand:Optional[List[str]]=Query(None,alias='expand[]')):
        # checking if posts_out schema needs some info from an external object (i.e username from user object).
        object_fields_mapping={} #holds object names as keys and list of values as value.
        for field,meta_data in schemas.posts_out.model_fields.items():
            if meta_data.description is not None:
                external_object=meta_data.description #by convention, the field's description will hold the name of the external object that said field depend on, represented as a single resource.
                if external_object not in object_fields_mapping:
                    object_fields_mapping[external_object]=[field]
                else:
                    object_fields_mapping[external_object].append(field)
        if object_fields_mapping!={}:
            cur.execute(f'''--sql
            WITH posts_out AS (SELECT * FROM posts WHERE ID=?),
            count_votes AS (SELECT COUNT(post) AS votes FROM votes where post=?),

            --creating a table for each object that post's schema depends on, and will append them with the relevant fields to the with section to include them all.
            --assuming that the table name is a representation of a resource as a collection (i.e users and not user).
            {",".join([f'''{external_object}_table AS (SELECT ID{f',{",".join(external_fields)}'} --selecting all relevant fields and ID
            FROM {external_object}s WHERE ID in (select {external_object} from posts_out)), --this where clause should,in theory, redude the size of the join table by reducing the size of one of the joined tables by filtering unnecessary rows before the join action.'''
            for external_object,external_fields in object_fields_mapping.items()])}
            -- join all the tables we included with the WITH statement, with filtering on posts_out.<external_object>=<external_object>_table.ID
            {f'''posts_joined AS (SELECT posts_out.*{f'{','.join([f'''{f''',{external_object}_table.
            {f",{external_object}_table.".join(external_fields)}'''}
            ''' for external_object,external_fields in object_fields_mapping.items()])}'}
            FROM posts_out CROSS JOIN 
            {'CROSS JOIN '.join([f'''{external_object}_table ON posts_out.{external_object}={external_object}_table.ID'''
            for external_object,external_fields in object_fields_mapping.items()])} )'''} --closing the post_joined statement
            SELECT posts_joined.*,COUNT(votes.post) as votes FROM posts_joined LEFT JOIN votes ON votes.post=posts_joined.ID GROUP BY posts_joined.ID
            ''',[id,id])
        else:
            cur.execute('''--sql
            WITH count_votes AS (SELECT COUNT(post) AS votes FROM votes where post=?)
            SELECT * FROM posts,count_votes WHERE posts.ID=?
            ''',[id,id])
        post=cur.fetchone()
        if not post:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"post with id {id} doesn't exist.")
        if expand and isinstance(expand,list):
            post=handle_expand(expand,post,schemas.posts_out,"posts")
        return post
    
    @router.post('/',response_model=schemas.posts_out,status_code=status.HTTP_201_CREATED)
    def create_post(post: schemas.posts_in,current_user:authSchemas.TokenData=Depends(oauth2.get_current_user)):
        post=schemas.posts_in(**post.dict())
        if post.content=="" and post.title=="":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="post title and content cannot be empty at the same time.")
        uuid=None
        #searching for available uuid
        while True:
            uuid=f"p_{uuid4().hex}"
            cur.execute('SELECT ID FROM posts WHERE ID=?',[uuid])
            if cur.fetchone() is None:
                break
        cur.execute(f'INSERT INTO posts(ID,user,{",".join(schemaKeysToStr(schemas.posts_in))}) VALUES(?,?,?,?)',[uuid,current_user.ID,post.title,post.content])
        db.commit()
        post=get_post(uuid)
        return post

    @router.delete('/{id}',status_code=status.HTTP_204_NO_CONTENT)
    def delete_posts(id:int,current_user=Depends(oauth2.get_current_user)):
        r'''
            Deletes a post created by this user.
        '''
        cur.execute('DELETE FROM posts WHERE user=? and ID=?',[current_user.ID,int(id)])
        if cur.rowcount==0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        db.commit()

    @router.delete('/',status_code=status.HTTP_204_NO_CONTENT)
    def delete_posts(current_user=Depends(oauth2.get_current_user)):
        r'''
            Deletes this users' posts.
        '''
        cur.execute('DELETE FROM posts WHERE user=?',[current_user.ID])
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