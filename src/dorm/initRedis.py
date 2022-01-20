from redis import Redis


r = Redis(host='my_redis', port=6379, decode_responses=True, charset='UTF-8', encoding='UTF-8')
print(r)

def setRedis():
    buildings = getBuildings()
    dataMale = [{'name': building[1].encode('utf-8').decode('utf-8'), 'dorm': getDorms(building[0], '男')} for building in buildings]
    dataFemale = [{'name': building[1].encode('utf-8').decode('utf-8'), 'dorm': getDorms(building[0], '女')} for building in buildings]
    r.delete('男')
    r.delete('女')
    for building in dataMale:
        r.lpush('男', building['name'])
        r.hmset(building['name'] + '男', building['dorm'])
    for building in dataFemale:
        r.lpush('女', building['name'])
        r.hmset(building['name'] + '女', building['dorm'])
    sql = 'select dorm.id as dorm_id, capacity, sex, building.name building_name from dorm, unit, building where dorm.unit_id=unit.id and building_id=building.id;'
    res = query(sql)
    for i in res:
        r.delete(i[3] + i[2] + str(i[1]))
    for i in res:
        r.lpush(i[3] + i[2] + str(i[1]), i[0])
    buildings = query('select id, name from building;')
    for building in buildings:
        r.set(building[1], building[0])
    sql = 'select username, user_info.id id, sex,authentication from user, user_info, user_authentication where user.uid=user_info.id and user_authentication.uid=user_info.id;'
    res = query(sql)
    for i in res:
        r.set(i[0] + 'ID', i[1])
        r.set(i[0] + 'SEX', i[2])
        r.set(i[3] + 'AUTH', i[0])