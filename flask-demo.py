# save this as app.py
import os
import sys
from flask import Flask, request

app = Flask(__name__)

@app.route("/")
def hello():
    return "Hello, World!"

@app.route("/llm")
def llm():
    return "Hello, I am Qwen-Max, I have over 10,000,000,000 parameters."

@app.route("/get", methods=["GET"])
def get():
    if request.method == "GET":
        content = request.args.get("key")
    return "key is " + content

@app.route('/user/<username>/')
def profile(username):
    return f'this is {username}\'s profile'

if __name__ == '__main__':
    print("正在启动 Flask 服务器，端口80", file=sys.stderr)
    app.run(host='0.0.0.0', port=80, debug=True)