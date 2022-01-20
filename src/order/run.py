import pika
import threading
import json
import pymysql
from redis import Redis
import time
import datetime
import random


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

def hasDorm(userId):
    if RedisConnection:
        try:  # 使用 Redis 缓存
            dormId = int(r.hget('dorm_user_{}'.format(userId), 'dorm'))
            if dormId:
                return True
            else:
                return False
        except:  # 直接访问 Mysql 数据库
            dorm = query('select dorm_id from user_dorm where uid={};'.format(userId))
            return bool(dorm)
    else:
        dorm = query('select dorm_id from user_dorm where uid={};'.format(userId))
        return bool(dorm)

def orderProcess(data):
    timeNow = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    username = data['username']
    sex = data['sex']
    building = data['building']
    orderInfo = data['orderInfo']
    if RedisConnection:
        try:
            buildingId = r.get('building_{}'.format(building))
        except:
            buildingId = query('select id from building where name="{}";'.format(building))[0][0]
    else:
        buildingId = query('select id from building where name="{}";'.format(building))[0][0]
    bind = data['bind']
    count = 1
    roommateIds = []
    code = 200
    if RedisConnection:
        try:  # 使用 Redis 缓存
            userId = r.get('username_{}'.format(username))
            if hasDorm(userId):  # 已经拥有宿舍
                code = 405
            if code == 200 and bind == 'true':
                authentications = data['auth'].split('.')
                for authentication in authentications:
                    roommateId = r.get('authentication_{}'.format(authentication))
                    if not roommateId or roommateId == userId:  # 认证码错误或认证码为自身
                        code = 401
                        break
                    roommateSex = r.get('sex_{}'.format(roommateId))
                    if roommateSex != sex:  # 性别不符
                        code = 402
                        break
                    if hasDorm(roommateId):  # 同住人已经拥有宿舍
                        code = 403
                        break
                    roommateIds.append(roommateId)
                    count += 1
        except:  # 直接访问 Mysql 数据库
            userId = query('select uid from user where username={};'.format(username))[0][0]
            if hasDorm(userId):  # 已经拥有宿舍
                code = 405
            if code == 200 and bind == 'true':
                authentications = data['auth'].split('.')
                for authentication in authentications:
                    roommateId = query('select uid from user_authentication where authentication={};'.format(authentication))
                    if not roommateId or roommateId == userId:  # 认证码错误或认证码为自身
                        code = 401
                        break
                    roommateSex = query('select sex from user_info where id={};'.format(roommateId))[0][0]
                    if roommateSex != sex:  # 性别不符
                        code = 402
                        break
                    if hasDorm(roommateId):  # 同住人已经拥有宿舍
                        code = 403
                        break
                    roommateIds.append(roommateId)
                    count += 1
    else:
        userId = query('select uid from user where username={};'.format(username))[0][0]
        if hasDorm(userId):  # 已经拥有宿舍
            code = 405
        if code == 200 and bind == 'true':
            authentications = data['auth'].split('.')
            for authentication in authentications:
                roommateId = query('select uid from user_authentication where authentication={};'.format(authentication))
                if not roommateId or roommateId == userId:  # 认证码错误或认证码为自身
                    code = 401
                    break
                roommateSex = query('select sex from user_info where id={};'.format(roommateId))[0][0]
                if roommateSex != sex:  # 性别不符
                    code = 402
                    break
                if hasDorm(roommateId):  # 同住人已经拥有宿舍
                    code = 403
                    break
                roommateIds.append(roommateId)
                count += 1
    maxCapacity = 8
    dormsId = []
    if code == 200:
        if RedisConnection:
            try:  # 使用 Redis 缓存
                for i in range(count, maxCapacity + 1):
                    if int(r.hget('{}_{}'.format(building, sex), i)) > 0:
                        dormsId.extend(r.lrange('{}_{}_{}'.format(building, sex, i), 0, -1))
            except:  # 直接访问 Mysql 数据库
                unitsId = query('select id from unit where building_id={};'.format(buildingId))
                unitsId = [str(i[0]) for i in unitsId]
                dormsId = query('select id from dorm where sex="{}" and unit_id in ({}) and capacity>={};'.format(sex, ', '.join(unitsId), count))
                dormsId = [i[0] for i in dormsId]
        else:
            unitsId = query('select id from unit where building_id={};'.format(buildingId))
            unitsId = [str(i[0]) for i in unitsId]
            dormsId = query('select id from dorm where sex="{}" and unit_id in ({}) and capacity>={};'.format(sex, ', '.join(unitsId), count))
            dormsId = [i[0] for i in dormsId]
    if code == 200:
        if not dormsId:  # 没有满足条件的宿舍
            code = 404
    if code == 200:
        dormId = random.choice(dormsId)
        print(dormsId, dormId)
        if RedisConnection:
            try:
                capacity = int(r.hget('dorm_dorm_{}'.format(dormId), 'capacity'))
                unitId = r.hget('dorm_dorm_{}'.format(dormId), 'unit')
                r.lrem('{}_{}_{}'.format(building, sex, capacity), 1, dormId)
                r.lpush('{}_{}_{}'.format(building, sex, capacity - count), dormId)
                r.hset('dorm_dorm_{}'.format(dormId), 'capacity', capacity - count)
                r.hset('{}_{}'.format(building, sex), capacity, int(r.hget('{}_{}'.format(building, sex), capacity)) - 1)
                r.hset('{}_{}'.format(building, sex), capacity - count, int(r.hget('{}_{}'.format(building, sex), capacity - count)) + 1)
                r.hset('dorm_user_{}'.format(userId), 'building', buildingId)
                r.hset('dorm_user_{}'.format(userId), 'unit', unitId)
                r.hset('dorm_user_{}'.format(userId), 'dorm', dormId)
                for roommateId in roommateIds:
                    r.hset('dorm_user_{}'.format(roommateId), 'building', buildingId)
                    r.hset('dorm_user_{}'.format(roommateId), 'unit', unitId)
                    r.hset('dorm_user_{}'.format(roommateId), 'dorm', dormId)
            except Exception as e:
                print(e)
        orderId = insert('insert into order_table(uid, building_id, num, sex, success, code, order_info, submit_time) values({}, {}, {}, "{}", {}, {}, "{}", "{}");'.format(userId, buildingId, count, sex, 'True', code, orderInfo, timeNow))
        unitId = query('select unit_id from dorm where id={};'.format(dormId))[0][0]
        print(orderId, userId, buildingId, unitId, dormId)
        insert('insert into order_info(order_id, uid, building_id, unit_id, dorm_id) values({}, {}, {}, {}, {});'.format(orderId, userId, buildingId, unitId, dormId))
        insert('insert into user_dorm(uid, dorm_id, create_time, is_valid) values({}, {}, "{}", {});'.format(userId, dormId, timeNow, 'True'))
        update('update dorm set capacity=capacity-{} where id={};'.format(count, dormId))       
        for roommateId in roommateIds:
            insert('insert into order_info(order_id, uid, building_id, unit_id, dorm_id) values({}, {}, {}, {}, {});'.format(orderId, roommateId, buildingId, unitId, dormId))
            insert('insert into user_dorm(uid, dorm_id, create_time, is_valid) values({}, {}, "{}", {});'.format(roommateId, dormId, timeNow, 'True'))
    else:
        orderId = insert('insert into order_table(uid, building_id, num, sex, success, code, order_info, submit_time) values({}, {}, {}, "{}", {}, {}, "{}", "{}");'.format(userId, buildingId, count, sex, 'False', code, orderInfo, timeNow))
    if RedisConnection:
        try:
            r.set('order_info_{}'.format(orderInfo), code)
        except:
            pass
    print('code:', code)

def getMessage(queue_name):
    credentials = pika.PlainCredentials('admin', 'admin')
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq', port=5672, virtual_host='/', credentials=credentials))
    channel = connection.channel()
    channel.queue_declare(queue=queue_name, durable=False)

    def callback(ch, method, properties, body):
        print(queue_name + ": [x] Received %r 开始处理" % body.decode())
        data = json.loads(body.decode())
        orderProcess(data)
        print(queue_name + ': 处理完毕')
        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=False)
    channel.start_consuming()

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
    return buildings

def getQueues():
    buildings = getBuildings()
    queues = []
    for building in buildings:
        queues.append('{}_男'.format(building))
        queues.append('{}_女'.format(building))
    return queues

def getRedisStatu():  # 每 1ms 确认一次 Redis 连接状态
    global RedisConnection
    while True:
        try:
            r.ping()
            RedisConnection = True
        except:
            RedisConnection = False
        time.sleep(0.001)

def main():
    time.sleep(20)
    queues = getQueues()
    for queue in queues:
        t = threading.Thread(target=getMessage, args=(queue,))
        t.start()
    t = threading.Thread(target=getRedisStatu)
    t.start()
    print('Order Service Started!', queues)

if __name__ == '__main__':
    main()