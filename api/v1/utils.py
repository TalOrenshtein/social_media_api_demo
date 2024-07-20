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