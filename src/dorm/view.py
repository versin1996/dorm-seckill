from flask import request, jsonify
import pymysql
from redis import Redis
import time
import threading


r = Redis(host='my_redis', port=6379, decode_responses=True, charset='UTF-8', encoding='UTF-8')
RedisConnection = True

config = {
    'host': 'webdb',
    'port': 3306,
    'user': 'root',
    'password': '123456',
    'db': 'webserver',
    'charset': 'utf8mb4'
}

def query(sql):
    conn = pymysql.connect(**config)
    cursor = conn.cursor()
    cursor.execute(sql)
    res = cursor.fetchall()
    conn.commit()
    conn.close()
    return res

def insert(sql):
    conn = pymysql.connect(**config)
    cursor = conn.cursor()
    cursor.execute(sql)
    cursor.execute('select LAST_INSERT_ID();')
    id = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return id

def update(sql):
    conn = pymysql.connect(**config)
    cursor = conn.cursor()
    cursor.execute(sql)
    conn.commit()
    conn.close()

def setRedis():
    r.flushdb()

    mysqlConnection = tuple()  # 判断数据库是否初始化完毕
    while not mysqlConnection:
        try:
            mysqlConnection = query('select id, name from building;')
        except:
            pass
        time.sleep(0.001)

    usernames = query('select uid, username from user;')
    for username in usernames:
        r.set('username_{}'.format(username[1]), username[0])  # username_<username>

    nameSexs = query('select id, name, sex from user_info;')
    for nameSex in nameSexs:
        r.set('name_{}'.format(nameSex[0]), nameSex[1])  # name_<uid>
        r.set('sex_{}'.format(nameSex[0]), nameSex[2])  # sex_<uid>

    authentications = query('select uid, authentication from user_authentication;')
    for authentication in authentications:
        r.set('authentication_{}'.format(authentication[0]), authentication[1])  # authentication_<uid>
        r.set('authentication_{}'.format(authentication[1]), authentication[0])  # authentication_<authentication>

    buildings = query('select id, name from building;')
    for building in buildings:
        r.set('building_{}'.format(building[0]), building[1])  # building_<building_id>
        r.set('building_{}'.format(building[1]), building[0])  # building_<building_name>
        tempBuildings = r.lrange('buildings', 0, -1)
        if building[1] not in tempBuildings:
            r.lpush('buildings', building[1])  # buildings
        for sex in ['男', '女']:
            units = query('select id, name from unit where building_id={};'.format(building[0]))
            for unit in units:
                r.set('unit_{}'.format(unit[0]), unit[1])  # unit_<unit_id>
            units = [str(i[0]) for i in units]
            maxCapacity = 8
            dorms = {}
            for i in range(0, maxCapacity + 1):
                sql = 'select id from dorm where sex="{}" and unit_id in ({}) and capacity={};'.format(sex, ', '.join(units), i)
                dormIds = [cap[0] for cap in query(sql)]
                capacity = len(dormIds)
                dorms[i] = capacity
                for dormId in dormIds:
                    r.lpush('{}_{}_{}'.format(building[1], sex, i), dormId)  # building_<男/女>_<capacity>
                    unitId, dormCapacity = query('select unit_id, capacity from dorm where id={};'.format(dormId))[0]
                    r.hmset('dorm_dorm_{}'.format(dormId), {'building': building[0], 'unit': unitId, 'capacity': dormCapacity})  # dorm_dorm_<dorm_id>
            r.hmset('{}_{}'.format(building[1], sex), dorms)  # building_<男/女>

    dormIds = query('select id, name from dorm;')
    for dormId in dormIds:
        r.set('dorm_{}'.format(dormId[0]), dormId[1])  # dorm_<dorm_id>

    orders = query('select uid, building_id, unit_id, dorm_id from order_info;'.format(username[0]))
    for order in orders:
        r.hset('dorm_user_{}'.format(order[0]), 'building', order[1])  # dorm_user_<uid>
        r.hset('dorm_user_{}'.format(order[0]), 'unit', order[2])  # dorm_user_<uid>
        r.hset('dorm_user_{}'.format(order[0]), 'dorm', order[3])  # dorm_user_<uid>

    accessToken = query('select access_token from qywx;')[0][0]
    r.set('access_token', accessToken)  # access_token

def hello():
    return jsonify(hello='world')

def getOrderTime():
    with open('settings.conf', 'r') as f:
        orderTime = f.readline().strip()
    # orderTime = '2022-1-20 00:36:00 GMT+0800'
    return jsonify(orderTime=orderTime)

def getAccessToken():
    if RedisConnection:
        try:
            accessToken = r.get('access_token')
            return jsonify(accessToken=accessToken)
        except:
            pass
    accessToken = query('select access_token from qywx;')[0][0]
    return jsonify(accessToken=accessToken)

def setAccessToken():
    accessToken = request.form['accessToken']
    if RedisConnection:
        try:
            r.set('access_token', accessToken)
        except:
            pass
    update('update qywx set access_token="{}";'.format(accessToken))
    return jsonify(code=200)

def getOrderResult():
    orderInfo = request.form['orderInfo']
    if RedisConnection: 
        try:
            code = r.get('order_info_{}'.format(orderInfo))
            while not code:
                time.sleep(0.01)
                code = r.get('order_info_{}'.format(orderInfo))
            code = int(code)
            return jsonify(code=code)
        except:
            pass
    res = query('select code from order_table where order_info={};'.format(orderInfo))
    while not res:
        time.sleep(0.1)
        res = query('select code from order_table where order_info={};'.format(orderInfo))
    code = int(res[0][0])
    return jsonify(code=code)

def getUserInfo():
    username = request.form['username']
    if RedisConnection: 
        try:
            userId = r.get('username_{}'.format(username))
            name = r.get('name_{}'.format(userId))
            sex = r.get('sex_{}'.format(userId))
            authentication = r.get('authentication_{}'.format(userId))
            return jsonify(name=name, sex=sex, authentication=authentication)
        except:
            pass
    userId = query('select uid from user where username={};'.format(username))[0][0]
    name, sex = query('select name, sex from user_info where id={};'.format(userId))[0]
    authentication = query('select authentication from user_authentication where uid={};'.format(userId))[0][0]
    return jsonify(name=name, sex=sex, authentication=authentication)

def hasDorm():
    username = request.form['username']
    if RedisConnection:   
        try:
            userId = r.get('username_{}'.format(username))
            dormId = r.hget('dorm_user_{}'.format(userId), 'dorm')
            if dormId:
                return jsonify(code=200)
            else:
                return jsonify(code=404)
        except:
            pass
    userId = query('select uid from user where username={};'.format(username))[0][0]
    dorm = query('select dorm_id from user_dorm where uid={};'.format(userId))
    if dorm:
        return jsonify(code=200)
    else:
        return jsonify(code=404)

def getUserDorm():
    username = request.form['username']
    if RedisConnection:   
        try:
            userId = r.get('username_{}'.format(username))
            buildingId = r.hget('dorm_user_{}'.format(userId), 'building')
            unitId = r.hget('dorm_user_{}'.format(userId), 'unit')
            dormId = r.hget('dorm_user_{}'.format(userId), 'dorm')
            buildingName = r.get('building_{}'.format(buildingId))
            unitName = r.get('unit_{}'.format(unitId))
            dormName = r.get('dorm_{}'.format(dormId))
            return jsonify(buildingName=buildingName, unitName=unitName, dormName=dormName)
        except:
            pass
    userId = query('select uid from user where username={};'.format(username))[0][0]
    buildingId, unitId, dormId = query('select building_id, unit_id, dorm_id from order_info where uid={};'.format(userId))[0]
    buildingName = query('select name from building where id={};'.format(buildingId))[0][0]
    unitName = query('select name from unit where id={};'.format(unitId))[0][0]
    dormName = query('select name from dorm where id={};'.format(dormId))[0][0]
    return jsonify(buildingName=buildingName, unitName=unitName, dormName=dormName)

def getBuildings():
    buildings = []
    while not buildings:
        if RedisConnection:   
            try:
                buildings = r.lrange('buildings', 0, -1)
            except:
                pass
        else:
            try:
                buildings = query('select name from building;')
                buildings = [building[0] for building in buildings]
            except:
                pass
        time.sleep(0.001)
    return jsonify(buildings=buildings)
    
def getList():
    sex = request.form['sex']
    data = {}
    if RedisConnection:    
        try:
            buildings = r.lrange('buildings', 0, -1)
            for building in buildings:
                data[building] = r.hgetall('{}_{}'.format(building, sex))
            return jsonify(data)
        except:
            pass
    buildings = query('select id, name from building;')
    for building in buildings:
        units = query('select id from unit where building_id={};'.format(building[0]))
        units = [str(i[0]) for i in units]
        maxCapacity = 8
        dorms = {}
        for i in range(1, maxCapacity + 1):
            sql = 'select count(*) from dorm where sex="{}" and unit_id in ({}) and capacity={};'.format(sex, ', '.join(units), i)
            capacity = query(sql)[0][0]
            dorms[i] = capacity
        data[building[1]] = dorms
    return jsonify(data)


def getRedisStatu():  # 每 1ms 确认一次 Redis 连接状态
    global RedisConnection
    prev = RedisConnection
    while True:
        try:
            r.ping()
            if prev == False:
                setRedis()
            RedisConnection = True
            prev = True
        except:
            RedisConnection = False
            prev = False
        time.sleep(0.001)

# time.sleep(15)
try:
    print('set redis cache')
    setRedis()
except:
    pass

t = threading.Thread(target=getRedisStatu)
t.start()