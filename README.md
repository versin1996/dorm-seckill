# 总体设计方案 - 新生选宿舍秒杀系统

> 整体设计方案为单机架设，不考虑使用分布式集群
>
> 下述方案在最终实现版本可能会有不一致，也许会有些功能难以实现而改用其他替代方案

## 1、总体架构图

![系统架构图](C:\Users\86135\Desktop\互联网软件开发\作业\小组项目\系统架构图.jpg)

## 2、系统易用性

#### 系统部署方式

+ docker-compose 一键部署

#### 系统使用便捷性

+ 一键部署
+ 动态配置秒杀时间，便于应对突发情况，修改秒杀时间点不必重启服务
+ 通过企业微信工作台进入服务，自动登录
+ 首页显示用户认证码与宿舍列表信息
+ 点击选择宿舍按钮进入选择宿舍界面
+ 选择宿舍完成后显示宿舍选择结果

#### 系统初始化

+ 启动服务时检查服务器是否存在 Mysql 数据库持久化文件，若有则加载该持久化文件，若没有则使用 sql 脚本文件进行数据库初始化
+ 在 Mysql 数据库启动完毕后将部分数据初始化缓存到 Redis 服务中

## 3、系统高并发

#### 前端优化

**静态文件压缩**：将 HTML 文件、JS 文件、CSS 文件等静态文件进行压缩

**动静分离**：将静态页面与动态数据分离开来，宿舍列表信息采用 AJAX 异步请求客户端渲染的方式来进行，以减轻服务端的压力

#### Redis 缓存

+ Mysql 数据库单机的并发量大致在1000左右，5K QPS 若直接打到 Mysql 数据库，基本上数据库服务会直接挂掉，因此会导致服务不可用，利用缓存可极大提高系统读写速度，故采用 Redis 缓存机制缓解直接访问 Mysql 数据库的压力
+ 根据 Redis 官方给出的读写测试数据，单机 Redis 能达到写 8W QPS，读 11W QPS，故能够满足选宿舍的需求

#### 多线程处理订单

+ 一个线程对应处理一个消息队列的订单请求，由于不同消息队列的订单请求的性别和楼均不同，Mysql 数据库采用 InnoDB 引擎，不会出现竞争行锁的情况，故能有效加快处理速度且不会出现数据不一致的情况
+ 采用多线程减缓了使用 RabbitMQ 消息队列所带来的串行处理订单造成用户等待处理时长

## 4、系统可靠性

#### RabbitMQ 解耦

+ 进行削峰处理，即异步处理过程，下订单与处理订单异步进行，订单处理服务根据自身处理能力从消息队列中拉取请求进行处理
+ 采用“发布-订阅”模式，前端向消息队列写入订单请求，后端服务从消息队列中取出订单请求并进行处理
+ 多个消息队列，按性别和楼进行拆分，将不同订单请求发送到不同的消息队列中
+ 消息持久化，防止 RabbitMQ 服务出现宕机导致未处理订单数据丢失

#### 一致性保证

+ 将修改 Redis 缓存内容与更新 Mysql 数据库内容看成一个原子操作，必须同时成功或同时失败
+ 若以上任意步骤出现问题，则回退到处理该订单前的状态

#### Redis 缓存出现宕机

+ 当 Redis 缓存服务出现宕机的情况，应及时重启 Redis 服务
+ 此时应保证可以通过直接查询 Mysql 数据库来保障服务的可用性

#### 处理订单服务出现宕机

+ 此时应保证从消息队列取出的未处理完成的订单请求不丢失
+ 故应该要求订单处理服务在处理完一个订单请求时才将该订单请求从消息队列中彻底移除

## 5、系统安全性

#### 白名单与 Token

+ 在开始秒杀前确定白名单
+ 只有在白名单的用户才能够获取 Token
+ 拥有 Token 的用户才能访问宿舍列表信息与秒杀服务

#### 禁止暴露外部端口

+ 除 NodeJS 以外所有的服务均不能够从外部进行访问，只允许内部容器间互相访问

#### 开始秒杀前生成订单URL

+ 宿舍信息、HTML 文件、CSS 文件、JS 文件等静态资源在秒杀前均可正常访问

+ 为了防止恶意刷单脚本，在秒杀开始前通过时间戳和 Hash 算法生成下订单 URL

#### 下单冷却与客户端验证

+ 为了避免刷单脚本，设置每 3 秒只能进行一次下订单请求
+ 在一段时间内下单超过一定次数的用户增加验证码答题或滑块验证
  + 防止作弊。早期秒杀器比较猖獗，存在恶意买家或竞争对手使用秒杀器扫货的情况，商家没有达到营销的目的，所以增加答题来进行限制
  + 延缓请求。零点流量的起效时间是毫秒级的，答题可以人为拉长峰值下单的时长，由之前的 <1s 延长到 <10s。这个时间对于服务端非常重要，会大大减轻高峰期并发压力；另外，由于请求具有先后顺序，答题后置的请求到来时可能已经没有库存了，因此根本无法下单，此阶段落到数据层真正的写也就非常有限了

## 6、系统详细设计

### 数据设计

#### Mysql 数据库设计

**用户信息表**`user_info`

| 字段   | 类型        | 含义   | 外键 |
| ------ | ----------- | ------ | ---- |
| id     | int         | 用户ID | —    |
| name   | varchar(20) | 姓名   | —    |
| stu_no | varchar(10) | 学号   | —    |
| sex    | varchar(5)  | 性别   | —    |

**用户表**`user`

| 字段     | 类型         | 含义         | 外键          |
| -------- | ------------ | ------------ | ------------- |
| id       | int          | 用户表项ID   | —             |
| uid      | int          | 用户ID       | user_info(id) |
| username | varchar(10)  | 用户名即学号 | —             |
| password | varchar(100) | MD5密码      | —             |
| is_del   | boolean      | 是否删除     | —             |

**用户认证表**`user_authentication`

| 字段           | 类型         | 含义           | 外键          |
| -------------- | ------------ | -------------- | ------------- |
| id             | int          | 用户认证表项ID | —             |
| uid            | int          | 用户ID         | user_info(id) |
| authentication | varchar(100) | 用户认证码     | —             |

**楼表**`building`

| 字段 | 类型        | 含义   | 外键 |
| ---- | ----------- | ------ | ---- |
| id   | int         | 楼ID   | —    |
| name | varchar(30) | 楼名称 | —    |

**单元表**`unit`

| 字段        | 类型        | 含义     | 外键         |
| ----------- | ----------- | -------- | ------------ |
| id          | int         | 单元ID   | —            |
| building_id | int         | 楼ID     | building(id) |
| name        | varchar(30) | 单元名称 | —            |

**宿舍表**`dorm`

| 字段           | 类型        | 含义         | 外键     |
| -------------- | ----------- | ------------ | -------- |
| id             | int         | 宿舍ID       | —        |
| unit_id        | int         | 单元ID       | unit(id) |
| name           | varchar(30) | 宿舍名称     | —        |
| sex            | varchar(5)  | 宿舍性别所属 | —        |
| total_capacity | int         | 宿舍总床位   | —        |
| capacity       | int         | 宿舍剩余床位 | —        |
| bad_count      | int         | 坏床数量     | —        |

**订单表**`order_table`

| 字段        | 类型         | 含义         | 外键          |
| ----------- | ------------ | ------------ | ------------- |
| id          | int          | 订单ID       | —             |
| uid         | int          | 用户ID       | user_info(id) |
| building_id | int          | 楼ID         | building(id)  |
| num         | int          | 共同选择人数 | —             |
| sex         | varchar(5)   | 性别         | —             |
| success     | boolean      | 是否成功     | —             |
| code        | int          | 错误码       | —             |
| order_info  | varchar(100) | 订单信息     | —             |
| submit_time | datetime     | 提交时间     | —             |

**订单详情表**`order_info`

| 字段        | 类型 | 含义           | 外键            |
| ----------- | ---- | -------------- | --------------- |
| id          | int  | 订单详情表项ID | —               |
| order_id    | int  | 订单ID         | order_table(id) |
| uid         | int  | 用户ID         | user_info(id)   |
| building_id | int  | 楼ID           | building(id)    |
| unit_id     | int  | 单元ID         | unit(id)        |
| dorm_id     | int  | 宿舍ID         | dorm(id)        |

**用户宿舍关联表**`user_dorm`

| 字段        | 类型     | 含义     | 外键          |
| ----------- | -------- | -------- | ------------- |
| id          | int      | 关联ID   | —             |
| uid         | int      | 用户ID   | user_info(id) |
| dorm_id     | int      | 宿舍ID   | dorm(id)      |
| create_time | datetime | 创建时间 | —             |
| is_valid    | boolean  | 是否有效 | —             |

**企业微信表**`qywx`

| 字段         | 类型         | 含义                     | 外键 |
| ------------ | ------------ | ------------------------ | ---- |
| id           | int          | 企业微信 access_token id | —    |
| access_token | varchar(500) | 企业微信 access_token    | —    |

#### Redis 缓存设计

| key                               | type   | field                    | value                          | 含义                   |
| --------------------------------- | ------ | ------------------------ | ------------------------------ | ---------------------- |
| username_\<username\>             | string | —                        | uid                            | 用户名对应的 uid       |
| name_\<uid\>                      | string | —                        | name                           | 用户姓名               |
| sex_\<uid\>                       | string | —                        | sex                            | 用户性别               |
| authentication_\<uid\>            | string | —                        | authentication                 | uid 对应的认证码       |
| authentication_\<authentication\> | string | —                        | uid                            | 认证码对应的 uid       |
| building_<building_id>            | string | —                        | building_name                  | 楼名                   |
| building_<building_name>          | string | —                        | building_id                    | 楼ID                   |
| unit_<unit_id>                    | string | —                        | unit_name                      | 单元名                 |
| dorm_<dorm_id>                    | string | —                        | dorm_name                      | 宿舍名                 |
| buildings                         | list   | —                        | [building1, building2, ...]    | 所有楼的名称           |
| building_<男/女>                  | hash   | 0 ~ 8                    | count                          | 楼中不同容量宿舍数量   |
| building\_<男/女>\_\<capacity\>   | list   | —                        | [dorm_id1, dorm_id2, ...]      | 楼中指定容量的宿舍列表 |
| dorm_user_\<uid\>                 | hash   | building, unit, dorm     | building_id, unit_id, dorm_id  | 用户宿舍信息           |
| dorm_dorm_\<dorm_id\>             | hash   | building, unit, capacity | building_id, unit_id, capacity | 宿舍所在信息           |
| order_info_<order_info>           | string | —                        | code                           | 订单状态码             |
| access_token                      | string | —                        | access_token                   | 企业微信 access_token  |

#### RabbitMQ 消息队列设计

+ 按楼与性别设置消息队列

+ 消息格式

  | 字段           | 类型   | 含义         |
  | -------------- | ------ | ------------ |
  | username       | string | 用户名       |
  | building       | string | 楼名称       |
  | bind           | bool   | 是否绑定选择 |
  | authentication | list   | 同住人认证码 |

### 接口设计

#### 登录服务

由企业微信 API 获取用户信息实现自动登录

#### 查询宿舍列表信息服务

###### 宿舍列表信息

**请求方式：**POST（**HTTP**）

**请求地址：**http://IP:5000/list

**请求参数说明：**

| 参数 | 必须 | 说明             |
| ---- | ---- | ---------------- |
| sex  | 是   | 性别，“男”或“女” |

**返回参数说明：**

| 参数 | 类型 | 说明         |
| ---- | ---- | ------------ |
| data | JSON | 宿舍列表信息 |

**业务逻辑：**

1、从 Redis 缓存中查询相应性别的宿舍列表信息并响应

2、若 Redis 缓存服务不可用，则直接查询 Mysql 数据库获取相应性别的数据并响应（其他服务同理）

###### 用户是否拥有宿舍

**请求方式：**POST（**HTTP**）

**请求地址：**http://IP:5000/hasdorm

**请求参数说明：**

| 参数     | 必须 | 说明   |
| -------- | ---- | ------ |
| username | 是   | 用户名 |

**返回参数说明：**

| 参数 | 类型 | 说明                                                         |
| ---- | ---- | ------------------------------------------------------------ |
| code | int  | 错误码，200表示该用户拥有宿舍，404表示该用户未拥有宿舍       |
| data | JSON | 若错误码为 200 则为用户所选宿舍的楼名称、单元名称、宿舍名称，若错误码为 404 则为空 |

**业务逻辑：**

1、从 Redis 缓存中查询该用户是否拥有宿舍并响应

2、若 Redis 缓存服务不可用，则直接查询 Mysql 数据库判断该用户是否拥有宿舍并响应（其他服务同理）

#### 下订单服务

**获取请求：**从 RabbitMQ 消息队列中拉取订单请求

**多线程：**按照楼名与性别分别处理不同的请求

**业务逻辑：**

1、根据用户名获取用户ID，用户性别

2、判断请求体是否存在 bind 值，若存在则进行多人绑定选择处理

3、多人绑定选择需进行同住人认证码、性别、是否拥有宿舍判定，若合法则进行下一步

4、根据楼名获取楼ID并获取该楼满足条件的宿舍列表并从中随机选择一个宿舍

5、选择成功后同时更新 Redis 缓存和 Mysql 数据库内容，保证数据一致性

6、若过程中任一判定失败则将订单信息写入 Mysql 数据库，success 字段填写 false

7、处理完毕将 RabbitMQ 消息队列相应订单请求彻底删除

#### Token 服务

所有服务均进行校验，包含加密与解密两个部分

###### 加密服务

**请求方式：**POST（**HTTP**）

**请求地址：**http://IP:6000/encode

**请求参数说明：**

| 参数    | 必须 | 说明 |
| ------- | ---- | ---- |
| payload | 是   | 载荷 |

**返回参数说明：**

| 参数  | 类型   | 说明         |
| ----- | ------ | ------------ |
| Token | string | Token 字符串 |

**业务逻辑：**

1、使用 Python 的 jwt 库对载荷字典进行加密

2、返回 Token 字符串

###### 解密服务

**请求方式：**POST（**HTTP**）

**请求地址：**http://IP:6000/decode

**请求参数说明：**

| 参数  | 必须 | 说明         |
| ----- | ---- | ------------ |
| Token | 是   | Token 字符串 |

**返回参数说明：**

| 参数    | 类型 | 说明                                                      |
| ------- | ---- | --------------------------------------------------------- |
| code    | int  | 错误码，200表示解密成功，401表示解密失败且 payload 返回空 |
| payload | dict | 进行加密时的载荷                                          |

**业务逻辑：**

1、使用 Python 的 jwt 库对 Token 进行解密

2、返回错误码和载荷

#### NodeJS 前端服务

使用 express web 框架进行开发

使用 axios 进行服务请求

进行路由跳转与服务分发

路由跳转表

| 路由   | 请求方式 | 请求服务                         | 请求服务地址                |
| ------ | -------- | -------------------------------- | --------------------------- |
| /      | POST     | 宿舍列表信息服务                 | http://dorm:5000/list       |
| /login | POST     | 登录服务                         | http://login:4000/login     |
| /order | GET      | 不请求，由 NodeJS 响应下订单页面 | —                           |
| /order | POST     | RabbitMQ 消息队列服务            | amqp://username:password@mq |

**下订单业务逻辑：**

1、连接 RabbitMQ 消息队列

2、先向宿舍列表信息服务请求是否拥有宿舍，若拥有宿舍则跳转到选择结果页面

3、获取表单中的 username、building、bind、authentication 数据

4、将数据整合并发送给 RabbitMQ 消息队列

5、每等待一段时间后向宿舍列表信息服务请求是否拥有宿舍，重复 3 次

6、若选择宿舍成功则跳转选择结果页面，若失败则提示用户选择宿舍失败，以便用户再次进行宿舍选择

### 页面设计

使用 WEUI 进行页面渲染

**欢迎页面即主页**

+ 该页面展示用户的个人信息，包括姓名、性别、学号、认证码
+ 同时该页面也展示宿舍列表信息

**下订单页面**

+ 可通过主页跳转到下订单页面
+ 页面提供楼的选择，同住人共同选择

**结果页面**

+ 在下订单成功选择宿舍后自动跳转到选择结果页面
+ 已有宿舍用户若再次进入下订单页面则跳转到选择结果页面

## 7、压力测试方案

使用 Apache Bench 模拟大量请求进行测试

更改代码使每个分支都能够进入以保证测试的有效性

#### 宿舍列表信息压力测试

```shell
ab -c5000 -n20000 -r http://IP:5000/list
```

#### 单人订单请求压力测试

```shell
ab -c5000 -n20000 -r http://IP/order
```

#### 多人订单请求压力测试

```shell
ab -c5000 -n20000 -r http://IP/order
```
