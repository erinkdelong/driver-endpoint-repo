from flask import Flask, request, jsonify
import redis
import os


app = Flask(__name__)

@app.route('/')
def home():
    return 'Hello, World!'


@app.route('/get_user_info')
def get_uder_info():
    params = request.args
    phone_number = params.get('phone_number')
    if not phone_number:
        return jsonify({'error': 'Phone number is required'}), 400
    
    # Connect to Redis
    redis_host = os.environ.get('REDIS_HOST', 'localhost')
    redis_port = int(os.environ.get('REDIS_PORT', 6379))    
    redis_client = redis.Redis(host=redis_host, port=redis_port)

    # Check if user exists in Redis
    user_info = redis_client.get(phone_number)
    if user_info:
        return jsonify({'user_info': user_info.decode('utf-8'), }), 200
    else:
        return jsonify({'error': 'User not found'}), 404

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5001))  # Defaults to 5001 if PORT is not set
    app.run(host="0.0.0.0", port=port)

