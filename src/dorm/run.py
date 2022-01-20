from flask import Flask, jsonify
from view import getList, getBuildings, getUserInfo, getUserDorm, hasDorm, getOrderResult, getAccessToken, setAccessToken, getOrderTime, hello


app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

app.add_url_rule('/list', 'list', getList, methods=['POST'])
app.add_url_rule('/building', 'building', getBuildings, methods=['GET'])
app.add_url_rule('/userinfo', 'userinfo', getUserInfo, methods=['POST'])
app.add_url_rule('/userdorm', 'userdorm', getUserDorm, methods=['POST'])
app.add_url_rule('/hasdorm', 'hasdorm', hasDorm, methods=['POST'])
app.add_url_rule('/orderresult', 'orderresult', getOrderResult, methods=['POST'])
app.add_url_rule('/accesstoken', 'accesstoken', getAccessToken, methods=['GET'])
app.add_url_rule('/setaccesstoken', 'setaccesstoken', setAccessToken, methods=['POST'])
app.add_url_rule('/ordertime', 'ordertime', getOrderTime, methods=['GET'])
app.add_url_rule('/hello', 'hello', hello, methods=['GET'])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)