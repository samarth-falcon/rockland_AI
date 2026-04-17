import os
from dotenv import load_dotenv
import mysql.connector

load_dotenv()

def connect_mysql_database():
    """
    The following function is used to connect the 
    mysql database. 
    """
    try:
        connection = mysql.connector.connect(
            host = os.getenv("database_host"),
            user =  os.getenv("database_user"),
            password = os.getenv("database_password"),
            database = os.getenv("database_name")
        )
        if connection.is_connected():
            return {"Message": connection, "status_code": 200}
    except Exception as e:
        print("❌ Error:", e)
        return {"Message": "connection_failed", "status_code": 500}

