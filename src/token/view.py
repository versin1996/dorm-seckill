from flask import request, jsonify, make_response
import jwt


def encode():
	data = request.form
	secret = 'helloworldos.urandom(24)'
	token = jwt.encode(payload=data, key=secret, algorithm='HS256')
	res = make_response(jsonify(token=token))
	res.headers['Access-Control-Allow-Origin'] = "*"
	res.headers['Access-Control-Allow-Methods'] = 'GET, POST'
	return res

def decode():
	token = request.form['token']
	secret = 'helloworldos.urandom(24)'
	try:
		data = jwt.decode(jwt=token, key=secret, algorithms='HS256')
		res = make_response(jsonify(code=200, data=data))
		res.headers['Access-Control-Allow-Origin'] = "*"
		res.headers['Access-Control-Allow-Methods'] = 'GET, POST'
		return res
	except:
		return jsonify(code=401, data={})