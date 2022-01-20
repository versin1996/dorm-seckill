from flask import request, jsonify
from managedb import existUsername, getPassword, encodePassword


def login():
	username = request.form['username']
	password = request.form['password']
	password = encodePassword(password)
	print(username, password)
	if not existUsername(username):  # 查询数据库是否存在该用户
		return jsonify(code=700)
	elif password != getPassword(username):  # 用户名与密码是否匹配
		return jsonify(code=701)
	return jsonify(code=200)