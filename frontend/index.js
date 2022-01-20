const express = require('express')
const ejs = require('ejs')
const path = require('path')
const querystring = require('querystring')
const cookieParser=require("cookie-parser")
const axios = require('axios')
const app = module.exports = express()
const amqp = require('amqplib/callback_api')

app.set('views', './views')
app.engine('html', ejs.__express)
app.set('view engine', 'html')
app.use(express.static(path.join(__dirname, 'static')))
app.use(express.urlencoded({ extended: false }))
app.use(cookieParser())


// 响应宿舍列表信息页面即首页
app.get('/', (req, res) => {
	let token = req.cookies.token
	if(req.query.code) {
		console.log('企业微信登录，weixin code:', req.query.code)
		axios.get('http://dorm:5000/accesstoken')
			.then((accessTokenRes) => {
				let access_token = accessTokenRes.data.accessToken
				let getInfoUrl = `https://qyapi.weixin.qq.com/cgi-bin/user/getuserinfo?access_token=${access_token}&code=${req.query.code}`
				axios.get(getInfoUrl).then((infoRes) => {
					console.log(infoRes.data.errcode)
					if(infoRes.data.errcode == 40029) {
						return res.end('access_token error!')
					}
					else if(infoRes.data.errcode != 0) {
						console.log('access_token expired!')
						axios.get('https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid=wx1d3765eb45497a18&corpsecret=qQt8qESyiegC6uYEb45JJ5HyflO9Hnl24_fZbnji95c')
							.then((qywxRes) => {
								let access_token = qywxRes.data.access_token
								axios.post('http://dorm:5000/setaccesstoken', querystring.stringify({'accessToken': access_token}))
									.then((setAccessTokenRes) => {
										return res.render('homepage')
									})
							})
					}
					else {
						let getInfoDetailUrl = `https://qyapi.weixin.qq.com/cgi-bin/user/get?access_token=${access_token}&userid=${infoRes.data.UserId}`
						axios.get(getInfoDetailUrl).then((infoDetailRes) => {
							axios.post('http://dorm:5000/userinfo', querystring.stringify({'username': infoDetailRes.data.userid}))
								.then((userinfoRes) => {
									let name = infoDetailRes.data.name
									let sex = infoDetailRes.data.gender == '1' ? '男' : '女'
									let username = infoDetailRes.data.userid
									let authentication = userinfoRes.data.authentication
									console.log('weixin data:', name, sex, username, authentication)
									axios.post('http://token:6000/encode', querystring.stringify({
										'name': name,
										'sex': sex,
										'username': username,
										'authentication': authentication
									})).then((tokenRes) => {
										res.cookie('token', tokenRes.data.token, {maxAge: 3600000})  // 将 token 存在 cookie 里，有效期为 1h
				  						res.render('homepage')
									})
								})
						})
					}
				})
			})
	}
	else if(token) {
		console.log("接口登录")
		axios.post('http://token:6000/decode', querystring.stringify({'token': token}))
			.then((tokenRes) => {
				if(tokenRes.data.code == 200) {
					return res.render('homepage')
				}
			})
	}
})

// 获取宿舍列表信息内容
app.get('/info', (req, res) => {
	let token = req.cookies.token
	if(token) {
		axios.post('http://token:6000/decode', querystring.stringify({'token': token}))
			.then((tokenRes) => {
				if(tokenRes.data.code == 200) {
					let sex = tokenRes.data.data.sex
					axios.post('http://dorm:5000/list', querystring.stringify({'sex': sex}))
						.then((listRes) => {
							let buildings = listRes.data
							res.end(JSON.stringify({
								'buildings': buildings,
								'name': tokenRes.data.data.name,
								'sex': tokenRes.data.data.sex,
								'username': tokenRes.data.data.username,
								'authentication': tokenRes.data.data.authentication
							}))
						})
				}
			})
	}
})


// 响应登录界面
app.get('/login', (req, res) => {
	res.render('login')
})

// 登录
app.post('/login', (req, res) => {
	axios.post('http://login:4000/login', querystring.stringify(req.body))
		.then((loginRes) => {
  			if(loginRes.data.code == 200) {
  				axios.post('http://dorm:5000/userinfo', querystring.stringify({'username': req.body.username}))
  					.then((userinfoRes) => {
  						let username = req.body.username
  						let name = userinfoRes.data.name
  						let sex = userinfoRes.data.sex
  						let authentication = userinfoRes.data.authentication
  						axios.post('http://token:6000/encode', querystring.stringify({
							'name': name,
							'sex': sex,
							'username': username,
							'authentication': authentication
						})).then((tokenRes) => {
							res.cookie('token', tokenRes.data.token, {maxAge: 3600000})  // 将 token 存在 cookie 里，有效期为 1h
							res.end('login success!')
						})
  					})
  			}
  			else {
  				res.end('wrong user！')
  			}
		})
})

// 响应选择宿舍页面
app.get('/order', (req, res) => {
	let token = req.cookies.token
	if(token) {
		axios.post('http://token:6000/decode', querystring.stringify({'token': token}))
			.then((tokenRes) => {
				let username = tokenRes.data.data.username
				axios.post('http://dorm:5000/hasdorm', querystring.stringify({'username': username}))
					.then((hasdormRes) => {
						let code = hasdormRes.data.code
						if(code == 200)
							res.redirect('/result')
						else
							res.render('order')
					})
			})
	}
})

// 获取楼名信息
app.get('/building', (req, res) => {
	axios.get('http://dorm:5000/building')
		.then((buildingRes) => {
			let data = buildingRes.data
			res.end(JSON.stringify(data))
		})
})

// 获取楼名信息
app.get('/ordertime', (req, res) => {
	axios.get('http://dorm:5000/ordertime')
		.then((ordertimeRes) => {
			let data = ordertimeRes.data
			res.end(JSON.stringify(data))
		})
})

// 初始化消息队列
setTimeout(function() {
	axios.get('http://dorm:5000/building')
		.then((buildingRes) => {
			let buildings = buildingRes.data.buildings
			amqp.connect('amqp://admin:admin@rabbitmq', (err0, conn) => {
				if(err0)
					throw err0
				conn.createChannel((err1, ch) => {
					if(err1)
						throw err1
					let exchange = 'direct_exchange'
					ch.assertExchange(exchange, 'direct', {durable: false})
					for(let i in buildings) {
						ch.assertQueue(buildings[i] + '_' + '男', {durable: false})
						ch.assertQueue(buildings[i] + '_' + '女', {durable: false})
						ch.bindQueue(buildings[i] + '_' + '男', exchange, buildings[i] + '_' + '男')
						ch.bindQueue(buildings[i] + '_' + '女', exchange, buildings[i] + '_' + '女')
					}
				})
			})
		})
}, 15000)

// 获取订单结果
function getOrderResult(orderInfo) {
	return new Promise((resolve, reject) => {
		axios.post('http://dorm:5000/orderresult', querystring.stringify({'orderInfo': orderInfo}))
			.then((orderresultRes) => {
				resolve(orderresultRes.data)
			})
			.catch((error) => {
				reject(error)
			})
	})
}

// 选择宿舍
setTimeout(function() {
	amqp.connect('amqp://admin:admin@rabbitmq', (err0, conn) => {
		if(err0)
			throw err0
		conn.createChannel((err1, ch) => {
			if(err1)
				throw err1
			let exchange = 'direct_exchange'
			app.post('/order', (req, res) => {
				axios.get('http://dorm:5000/ordertime')
					.then((ordertimeRes) => {
						let data = ordertimeRes.data
						let now = new Date().getTime()
						orderTime = new Date(data.orderTime).getTime()
						console.log(now, orderTime)
						if(now < orderTime) {
							return res.end('250')
						}
						console.log(req.body)
						axios.post('http://token:6000/decode', querystring.stringify({'token': req.body.token}))
							.then(async (tokenRes) => {
								if(tokenRes.data.code == 200) {
									let sex = tokenRes.data.data.sex
									let username = tokenRes.data.data.username
									let severity = req.body.building + '_' + sex
									let time = process.hrtime()
									let orderInfo = username + time[0].toString() + time[1].toString()
									ch.publish(exchange, severity, Buffer.from(JSON.stringify({
										'username': username,
										'sex': sex,
										'building': req.body.building,
										'bind': req.body.bind,
										'auth': req.body.auth,
										'orderInfo': orderInfo
									})))
									let result = await getOrderResult(orderInfo)
									if(result.code == 200)
										res.end('200')
									else
										res.end('404')
								}
							})
					})
			})
		})
	})
}, 15000)


// 响应订单结果页面
app.get('/result', (req, res) => {
	res.render('orderDetail')
})

// 查询订单结果
app.post('/result', (req, res) => {
	axios.post('http://token:6000/decode', querystring.stringify({'token': req.body.token}))
		.then((tokenRes) => {
			if(tokenRes.data.code == 200) {
				let username = tokenRes.data.data.username
				axios.post('http://dorm:5000/userdorm', querystring.stringify({'username': username}))
					.then((userdormRes) => {
						let data = userdormRes.data
						res.end(JSON.stringify(data))
					})
			}
		})
})



let port = 8000
app.listen(port)
console.log(`http://127.0.0.1:${port}`)