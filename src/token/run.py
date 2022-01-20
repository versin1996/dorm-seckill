from flask import Flask
from view import encode, decode


app = Flask(__name__)

app.add_url_rule('/encode', 'encode', encode, methods=['POST'])
app.add_url_rule('/decode', 'decode', decode, methods=['POST'])


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6000, debug=True)