import pymysql
import hashlib


config = {
    'host': 'webdb',
    'port': 3306,
    'user': 'root',
    'password': '123456',
    'db': 'webserver',
    'charset': 'utf8mb4'
}

def existUsername(username):
    conn = pymysql.connect(**config)
    cursor = conn.cursor()
    sql = 'select * from user where username="{}";'.format(username)
    cursor.execute(sql)
    res = cursor.fetchone()
    conn.commit()
    conn.close()
    return bool(res)

def getPassword(username):
    conn = pymysql.connect(**config)
    cursor = conn.cursor()
    sql = 'select password from user where username="{}";'.format(username)
    cursor.execute(sql)
    conn.close()
    return cursor.fetchall()[0][0]

def encodePassword(password):
    first = hashlib.md5(password.encode(encoding='utf-8')).hexdigest()
    second = hashlib.md5(first.encode(encoding='utf-8')).hexdigest()
    return second