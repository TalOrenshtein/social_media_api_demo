#import psycopg2.pool,psycopg2.extras
from psycopg_pool import ConnectionPool
import psycopg_pool
from psycopg.rows import dict_row
from config import env
import atexit

db_pool=ConnectionPool(
        min_size=env.DB_MIN_CONNS,
        max_size=env.DB_MAX_CONNS,
        kwargs={"user":env.DB_USERNAME,
        "password":env.DB_PASSWPRD,
        "host":env.DB_HOSTNAME,
        "port":env.DB_PORT,
        "dbname":env.DB_NAME,
        "row_factory":dict_row,
        "autocommit":True
        }
    )

class DB():
    r'''
    This class is responsible of the recycling of cons.
    '''
    #db_con_pool=psycopg2.pool.ThreadedConnectionPool(3,10,
    # user=env.DB_USERNAME,
    # password=env.DB_PASSWPRD,
    # host=env.DB_HOSTNAME,
    # port=env.DB_PORT,
    # dbname=env.DB_NAME)

    db_con_pool=None
    @classmethod
    def __init_connectin_pool(cls):
        cls.db_con_pool=ConnectionPool(
            min_size=1,#env.DB_MIN_CONNS,
            max_size=1,#env.DB_MAX_CONNS,
            kwargs={"user":env.DB_USERNAME,
            "password":env.DB_PASSWPRD,
            "host":env.DB_HOSTNAME,
            "port":env.DB_PORT,
            "dbname":env.DB_NAME}
        )
        print('here_init_pool')

    @classmethod
    def close_pool(cls):
        print("clopsing pool")
        if cls.db_con_pool is not None:
            cls.db_con_pool.close()
            cls.db_con_pool=None

    def __init__(self):
        if DB.db_con_pool is None:
            DB.__init_connectin_pool()

        self.__con=DB.db_con_pool.getconn()
        self.__con.autocommit=True
        self.__cur=self.__con.cursor(row_factory=dict_row)#cursor_factory=psycopg2.extras.RealDictCursor)

    def __enter__(self):
        return self

    def __exit__(self,exc_type, exc_value, traceback):
        r'''
        recycling con before exiting WITH block
        '''
        print('here_exit')
        self.__del__()

    def __del__(self):

        r'''
        recycling con before destroying obj.
        '''
        print('here_del')
        if DB.db_con_pool is None:
            print('here_pool_none')
            return
        if self.__cur is not None:
            self.__cur.close()
        if self.__con is not None:
            try: 
                DB.db_con_pool.putconn(self.__con)
                print('con putted')
            except ValueError as e:
                #ignoring "can't return connection to pool 'pool-<x>', it doesn't come from any pool"
                if str(e).find("it doesn't come from any pool")==-1:
                    raise e
                else:
                    print(DB.db_con_pool.get_stats())
                    #This error is returned every time the app restarts for some reason.
                    #TODO: find another way to close the pool when the app's closing
                    #DB.db_con_pool.close()
                    print('here_close_pool')

    def sql_exec(self,query:str,args:tuple=())->list:
        r'''
        execute sql query and return a list of results.
        '''
        self.__cur.execute(query,args)
        res=None
        try: res=self.__cur.fetchall()
        except: #nothing to fetch, probably not a select statement.
            self.__con.commit()
        return None if res is None or len(res)==0 else res

    def sql_exec_file(self,file_path:str)->list:
        r'''
        execute sql file and return a list of results.
        '''
        with open(file_path,'r') as file:
            self.__cur.execute(file.read(),())
            res=None
            try: res=self.__cur.fetchall()
            except:  #nothing to fetch, probably not a select statement.
                self.__con.commit()
            return None if res is None or len(res)==0 else res
    
    def getCon(self):
        return self.__con
    
    def getCur(self):
        return self.__cur