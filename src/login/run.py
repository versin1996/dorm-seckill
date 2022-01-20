from flask import Flask 
from view import login


app = Flask(__name__)

app.add_url_rule('/login', 'login', login, methods=['POST'])


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4000, debug=True)