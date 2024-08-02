from pydantic import BaseModel,SerializeAsAny
from fastapi import HTTPException,status
from passlib.context import CryptContext
import sqlite3
from copy import deepcopy
from config import env
from typing import get_args,get_origin,Union,Annotated

def hashPW(pw:str):
    #set up pw hashing
    pw_context=CryptContext(schemes=['bcrypt'],deprecated='auto')
    return pw_context.hash(pw)

def verifyPW(attemped_pw,user_pw):
    pw_context=CryptContext(schemes=['bcrypt'],deprecated='auto')
    return pw_context.verify(attemped_pw,user_pw)

def schemaKeysToStr(schema:BaseModel)->list:
    r'''
    convert a schema to a list of keys
    '''
    return [key for key in schema.model_fields]

def getAPIs_rowFactory():
    r'''
    return a lambda functon that instructs sqlite3 to return the results as dict.
    '''
    return lambda c, r: dict(zip([col[0] for col in c.description], r))

def get_sql_schema(table:str)->dict:
    r'''
    get a dict with the columns as keys and their types as values
    :returns: a dict with the columns as keys and their types as values
    '''
    with sqlite3.connect('social_media_api.db', check_same_thread=False) as db:
        #set up cursor
        cur=db.cursor()
        #turn on foreign keys
        cur.execute('PRAGMA foreign_keys = ON;')

        #verify that the input is an actual table, and get its' schema
        cur.execute('''--sql
            SELECT name,sql FROM sqlite_master
            WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%'
            UNION ALL
            SELECT name,sql FROM sqlite_temp_master
            WHERE type IN ('table','view')
            ORDER BY 1
        ''')
        tables=cur.fetchall()
        for e in tables:
            if e[0]==table:
                fields=e[1].split(table)[1].strip('(),\n').splitlines()
                if fields[-1].strip().startswith('FOREIGN'):
                    fields.pop(-1)
                schema={}
                for i in range(len(fields)):
                    fields[i]=fields[i].strip().rstrip(',')
                    key,value=fields[i].split(' ',1)
                    schema[key]=value
                return schema
        raise ValueError(f'{table} table not found.')

def get_depenable_model(metadata)->BaseModel|None:
    r'''
    searching a pydantic model's metadata for dependentable model.
    :param metadata: A pydantic model's metadata (from model.model_fields)
    :returns: A list that list all the dependable fields, depending if dependable_fields is True/False.
    '''
    model=None
    if get_origin(metadata.annotation) is Union:
            for arg in get_args(metadata.annotation):
                if get_origin(arg) is Annotated and type(get_args(arg)[1]) is SerializeAsAny: # assuming all polymorphism was enabled via using SerializeAsAny
                    model=get_args(arg)[0]
    elif issubclass(metadata.annotation,BaseModel):
        model=metadata.annotation
    return model

def expand_response(src:str,destList:list,src_model:BaseModel)->dict|None:
    r'''
    get the detail of the requested dests until depth of env.EXPAND_MAX_DEPTH nested dests
    :param str src: The type of the source object that requested the expandation
    :param list destList: A list of dicts that includes the following key (type) value pairs:
        * type: (str): The destation which was requests. dest might be nested.
        * id (dict): The src's object id. If dest is nested, it's the id of the first object
    :param  BaseModel src_model: The source's response model
    :returns: A dict with dest's details in it, or none if not found.
    '''
    destList.sort(key=lambda e:e['type'].count("."))
    srcHolder=src #saving the original source to use for each elemenet in destList
    res={}
    memo={} #using memoraztion technique to avoid unnecessary helper calls when possible, to try and reduce load on the db. It seems reasonable to memo as the user probably won't expand too many unique fields, and in general it still keeps the space complexity at O(n).
    for dest in destList:
        src=srcHolder
        dests=[3.1415] #helps imitating do-while loop
        res_traveler=res #will travel to dest's depth to build the result, starting with depth 0.
        while len(dests)>0:
            dests=dest['type'].split('.')[:env.EXPAND_MAX_DEPTH]
            try:
                get_sql_schema(f'{dests[0]}s')
            except ValueError:
                try:
                    get_sql_schema(f'{dests[0]}')
                except:
                    raise ValueError(f"field '{dests[0]}' isn't expandable.")
            if not memo:
                memo={}
            if f'{dests[0]}@{dest['id']}' not in memo:
                dest_object=expand_response_helper(
                    src,
                    {"type":dests[0],"id":dest['id']},
                    src_model
                )
                memo[f'{dests[0]}@{dest['id']}']=dest_object
                res_traveler[dests[0]]=memo[f'{dests[0]}@{dest['id']}']
                if len(dests)>1:
                    dest['id']=memo[f'{dests[0]}@{dest['id']}'][f'{dests[1]}']
            else:
                res_traveler[dests[0]]=memo[f'{dests[0]}@{dest['id']}']
                if len(dests)>1:
                    dest['id']=memo[f'{dests[0]}@{dest['id']}'][dests[1]]
            res_traveler=res_traveler[dests[0]]
            src=dests[0]
            dests.pop(0)
            
            dest['type']=".".join(dests)
    return res

def expand_response_helper(src:str,dest:dict,src_model,sql_instead_of_pydantic:bool=False)->dict|None:
    r'''
    get the dest object of the requested dest with depth of 1
    :param str src: The type of the source object that requested the expandation
    :param dict dest: A dict that includes the following key (type) value pairs:
        * type: (str): The destation which was requests. dest might be nested.
        * id (dict): The src's object id. If dest is nested, it's the id of the first object
    :param  BaseModel src_model: The source's response model
    :param boo sql_instead_of_pydantic: will judge if dest['type'] is related to src using SQL table column names instead of pydantic models (not sure myself which is better to use)
    :returns: A dict with dest's details in it, or none if not found.
    '''
    #validating that dest is related to src.
    independable_fields=[]
    for field,meta_data in src_model.model_fields.items():
        if meta_data.description is None: #by convention, the field's description will hold the name of the external object that said field depend on, represented as a single resource.
            independable_fields.append(field)
    try:
        related=dest['type'] in get_sql_schema(f'{src}s') if  sql_instead_of_pydantic else dest['type'] in independable_fields
    except ValueError:
        try:
            related=dest['type'] in get_sql_schema(f'{src}') if  sql_instead_of_pydantic else dest['type'] in independable_fields
        except _:
            raise ValueError(f"{dest['type']} isn't related to {src}")
    if not related:
        raise ValueError(f"{dest['type']} isn't related to {src}")
    #getting dest's info
    with sqlite3.connect('social_media_api.db', check_same_thread=False) as db:
        #set up cursor
        cur=db.cursor()
        #turn on foreign keys
        cur.execute('PRAGMA foreign_keys = ON;')
        #set up row factory so SQL will return the results as a dict.
        cur.row_factory=getAPIs_rowFactory()
        cur.execute(f'''--sql
            SELECT * FROM {dest['type']}s WHERE ID=?
        ''',[dest['id']]) #TODO: find more elegant solution to this ugly {dest['type']}s
        return cur.fetchone()

def handle_model_fields_dependencies(data:dict,response_model:BaseModel)->dict:
    r'''
    Making a dict that's ready for unpacking to pydantic model while getting values for fields that depends on an external object
    :param dict data: A data for a pydentic model which is not necessary ready to be unpacked due to unhandled fields that're dependent of an external object.
    :param: BaseModel response_model: A pydentic response model schema which the data will be based on.
    :returns: a ready to unpack dict.
    '''
    object_fields_mapping={} #holds object names as keys and list of values as value.
    for field,meta_data in response_model.model_fields.items():
        if meta_data.description is not None:
            external_object=meta_data.description #by convention, the field's description will hold the name of the external object that said field depend on, represented as a single resource.
            if external_object not in object_fields_mapping:
                object_fields_mapping[external_object]=[field]
            else:
                object_fields_mapping[external_object].append(field)
        else:
            #create model recursively (nested models might have dependent fields in them as well)
            model=get_depenable_model(meta_data)
            if model:
                data[field]=handle_model_fields_dependencies(data[field],model)
    with sqlite3.connect('social_media_api.db', check_same_thread=False) as db:
        #set up cursor
        cur=db.cursor()
        #turn on foreign keys
        cur.execute('PRAGMA foreign_keys = ON;')
        #set up row factory so SQL will return the results as a dict.
        cur.row_factory=getAPIs_rowFactory()
        #querying each object table for the wanted fields and adding it to data
        for obj in object_fields_mapping:
            #by convention, obj is written as a single resource and not a collection resource like the resources appears as sql table names or url paths
            obj_id=data[obj] if isinstance(data[obj],str) else data[obj]['ID']
            cur.execute(f'''--sql
            SELECT {",".join(object_fields_mapping[obj])} from {obj}s where ID=?
            ''',[obj_id])
            extentions=cur.fetchone()
            for key,value in extentions.items():
                data[key]=value
    return data

def handle_expand(expand:list,obj_data:dict,obj_response_model:BaseModel,obj_title_collection_resource:str)->dict:
    r'''
    Handling expandtion
    :param list expand: list of string, where each element is a string represent an expandtion request.
    :param dict obj_data: The object's data before the expandtion
    :param BaseModel obj_request_model:The object's reponse (out) pydantic model
    :param str obj_title_collection_resource: a string that represent the name of the object resource, as a collection. For example: users,posts,accounts etc.
    :returns: a ready to unpack dict. returns None if expand is None or empty.
    '''
    if expand and len(expand)>0:
        destList=[]
        for e in expand:
            nested_field_dot=e.find('.') #getting a list of nesting fields
            firstDest=e[:nested_field_dot] if nested_field_dot>-1 else e
            destList.append({'type':f"{e}","id":obj_data[f'{firstDest}']})
        try:
            expandation=expand_response(obj_title_collection_resource,destList,obj_response_model)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail=str(e))
        #unpacking while doing a union with the sql query for fields that wasn't expanded.
        schema_convertion_dict={}
        for field,meta_data in obj_response_model.model_fields.items():
            if field in expandation:
                model=get_depenable_model(meta_data)
                if model:
                    schema_convertion_dict[field]=handle_model_fields_dependencies(expandation[field],model)
            else:
                schema_convertion_dict[field]=obj_data[field]
        return schema_convertion_dict