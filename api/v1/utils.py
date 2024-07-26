from pydantic import BaseModel
from passlib.context import CryptContext
import sqlite3

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

def expand_response(src:str,dest:dict,res:dict=None)->dict|None:
    r'''
    get the detail of the requested dests until depth of 4 nested dests
    :param str src: The type of the source object that requested the expandation
    :param dict dest: A dict that includes the following key (type) value pairs:
        * type: (str): The destation which was requests. dest might be nested.
        * id (dict): The src's object id. If dest is nested, it's the id of the first object
    :returns: A dict with dest's details in it, or none if not found.
    '''
    dests=dest['type'].split('.')[:4]
    try:
        get_sql_schema(f'{dests[0]}s')
        #dests[0]=f'{dests[0]}s' #TODO: is needed? don't think so because we don't only accessing it's table, but use it as a field too
    except ValueError:
        try:
            get_sql_schema(f'{dests[0]}')
        except _:
            raise ValueError(f"couldn't find {dests[0]}'s table in DB")
    if not res:
        res={}
    #using memoraztion technique to avoid unnecessary recursion calls when possible
    if f'{dests[0]}@{dest['id']}{f"${dests[1]}" if len(dests)>1 else ""}' in res:
        return res[f'{dests[0]}@{dest['id']}{f"${dests[1]}" if len(dests)>1 else ""}'] #TODO: CHECK! not sure it's correct.
    last=expand_response_helper(
        src,
        {"type":dests[0],"id":dest['id']},
        dests[1] if len(dests)>1 else None
    )
    res[f'{dests[0]}@{dest['id']}{f"${dests[1]}" if len(dests)>1 else ""}']=last
    src=dests[0]
    dests.pop(0)
    if len(dests)==0:
        return last
    dest['id']=last[f'{dests[0]}']
    dest['type']=".".join(dests)
    return expand_response(src,dest,res)


def expand_response_helper(src:str,dest:dict,wanted:str=None)->dict|None:
    r'''
    get the detail of the requested dest with depth of 1
    :param str src: The type of the source object that requested the expandation
    :param dict dest: A dict that includes the following key (type) value pairs:
        * type: (str): The destation which was requests. dest might be nested.
        * id (dict): The src's object id. If dest is nested, it's the id of the first object
    :returns: A dict with dest's details in it, or none if not found.
    '''
    #validating that dest is related to src.
    print(f"src: {src},\ndest: {dest},\nwanted: {wanted}")
    try: #TODO: If you can do it with schemas instead, it'd be great.
        related=dest['type'] in get_sql_schema(f'{src}s')
    except ValueError:
        try:
            related=dest['type'] in get_sql_schema(f'{src}')
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
            SELECT {'*' if not wanted else wanted} FROM {dest['type']}s WHERE ID=?
        ''',[dest['id']]) #TODO: find more elegant solution to this ugly {dest['type']}s
        return cur.fetchone() if not wanted else cur.fetchone[f'{wanted}']
