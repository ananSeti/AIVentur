import mysql.connector
import logging
from collections import defaultdict
def create_connection():
    return mysql.connector.connect(
    host="localhost",
    user="asl",
    password="anan1234",
    database="asl"
    )

def register_member(username,password,email):
    connection = create_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("INSERT INTO members (username,password,email) VALUES(%s,%s,%s) " ,
                       (username,password,email))
        connection.commit()
        print("Member register success")
        logging.info(f"Member register sucess")
    except Exception as e:
        print("Error register Member : {e} ")
        logging.error(f"Error register Member : {e}")
    finally:
        cursor.close()
        connection.close()

def login(username,password):
    connection = create_connection()
    cursor = connection.cursor()
    error = None 
    try:
        cursor.execute("SELECT * from members WHERE username =%s AND password = %s",
                       (username,password))
        user = cursor.fetchone()
        if user:
            print("login success")
            logging.info(f"login success : {username}")
            return user
        else:
            print(" login user or password incorrect")
            logging.error(f"login user or password incorrect: {username}")
    except Exception as e:
        print(f"Error login : {e}")
        logging.error(f"Error: {e}") 
        return error   
    finally:
        cursor.close()
        connection.close()

def get_user(user_id : int):
    connection = create_connection()
    cursor = connection.cursor()
    error = None 
    try:
       
        #sql =  "SELECT * from members WHERE id  =%s ",(user_id,)
        #print(sql)
        cursor.execute("SELECT * from members WHERE id  =%s ",
                       (user_id,))
        user = cursor.fetchone()
        if user:
            print("get user Id success")
            logging.info(f" get user id  success : {user_id}")
            return user
        else:
            print("  get user id user or password incorrect")
            logging.error(f"login user or password incorrect: {user_id}")
    except Exception as e:
        print(f"Error - get_user: {e}")
        logging.error(f"Error -get_user : {e}") 
        return error   
    finally:
        cursor.close()
        connection.close()
