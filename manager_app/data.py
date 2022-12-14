from dataclasses import dataclass
from frontend.config import Config
import mysql.connector as MySQL
from mysql.connector import errorcode
from datetime import datetime

class Data:
    '''
    This class creates a cursor to achieve DB access. 
    '''
    cursor = None
    cnx = None

    def __init__(self):
        try:
            self.cnx = MySQL.connect(
                user=Config.DB_CONFIG["user"],
                password=Config.DB_CONFIG["password"],
                host=Config.DB_CONFIG["host"],
                database=Config.DB_CONFIG["database"]
            )
        except MySQL.Error as err:
            if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                print("Something is wrong with your user name or password")
            elif err.errno == errorcode.ER_BAD_DB_ERROR:
                print("Database does not exist")
            else:
                print(err)
        print(" - Frontend DB connection success.")

        self.cursor = self.cnx.cursor(buffered=True)

    def add_entry(self, key, filename):
        '''
        Inserts an entry into DB. This function will generate a datetime. If the entry is already exist, it will be replaced by new one.
        '''
        now = datetime.now()
        fixed_now = now.strftime('%Y-%m-%d %H:%M:%S')

        query = """
                SELECT * FROM `pairs` where `key`='{}';
                """.format(key)
        self.cursor.execute(query)
        self.cnx.commit()
        data = self.cursor.fetchall()
        print(" - Frondend.data.add_entry: data will be empty if no duplication. v:data", data)

        if len(data) != 0:
            query = """
                    UPDATE `pairs`
                    SET `filename`='{}', `upload_time`='{}'
                    WHERE `key`='{}';
                    """.format(filename, fixed_now, key)
        else:
            query = """
                    INSERT INTO `pairs` (`key`,`filename`,`upload_time`)
                    VALUES ("{}", "{}", "{}");
                    """.format(key, filename, fixed_now)

        print(" - Frontend.data.add_entry: query => \n",query)

        self.cursor.execute(query)
        self.cnx.commit()
        
    def inspect_all_entries(self):
        '''
        Return all entries.
        '''
        query = """
                SELECT * FROM `pairs`;
                """

        self.cursor.execute(query)
        self.cnx.commit()
        data = self.cursor.fetchall()

        # print(data)
        return data

    def search_key(self, key):
        '''
        Search a given key in DB. 
        '''
        query = """
                SELECT * FROM `pairs` WHERE `key`="{}";
                """.format(key)

        
        self.cursor.execute(query)
        self.cnx.commit()
        data = self.cursor.fetchall()

        print("searched data :", data)
        return data

    #get the data from the statistics table
    #this function will return the latest statistics in the table
    def get_stat_data(self):
        '''
        Get the data from the statistics table.

        This function will return the latest statistics in the table
        '''
        query = """
                select * from statistics
                ORDER BY `id` DESC
                LIMIT 120;
                """
        self.cnx.commit()
        self.cursor.execute(query)
        print("Statistics Query Executed")
        data = self.cursor.fetchall()
        # print("Statistics data at backend: ", data)
        return data

    def get_keys(self):
        '''
        This function will returen all keys in pair table
        '''
        query = """
                SELECT `key` FROM pairs;
                """
        self.cnx.commit()
        self.cursor.execute(query)
        data = self.cursor.fetchall()
        return data

    def delete_all_entries(self):
        query = '''
                delete from pairs;
                '''
        self.cursor.execute(query)
        self.cnx.commit()

        query = '''
                delete from statistics;
                '''
        self.cursor.execute(query)
        self.cnx.commit()

    #get the data from the configuration table
    #this function will return the latest memcache config
    def get_config_data(self):
        #select the latest configuraiton from the database
        query = """
                SELECT * FROM configuration WHERE id = (
                    SELECT MAX(id) From configuration
                )
                """
        self.cursor.execute(query)
        print(" - Backend.data.get_config_data: Config Query Executed.")
        data = self.cursor.fetchall()
        return data
    
    #insert into the configuration database
    #capacity: the capacity of the memcache
    #policy: 0 for Random Replacement, 1 for Least Recently Used
    def insert_config_data(self,capacity,policy):

        query = """
                INSERT INTO `configuration` (`capacity`,`replacePolicy`)
                VALUES("{}","{}");
        """.format(capacity,policy)

        self.cursor.execute(query)
        self.cnx.commit()