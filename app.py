from flask import Flask, request, jsonify
import redis
import os

app = Flask(__name__)

@app.route('/')
def home():
    return 'Hello, World!'


@app.route('/get_data')
def get_data():
    return 'Hello, World- in data endpoint!'

if __name__ == '__main__':
    app.run(debug=True)
