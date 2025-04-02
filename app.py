from flask import Flask, request, jsonify
import redis
import os
from urllib.parse import urlparse


app = Flask(__name__)

print("Available environment variables:", [k for k in os.environ.keys()])

# Redis Configuration
redis_url = os.getenv('REDIS_URL')
#  manually set redis url
# Redis Configuration
# redis_url = "redis://default:BVLhJmQCYdYPzlYaOUNAzgQGPYpTrzKp@redis.railway.internal:6379"
print(f"Connecting to Redis at: {redis_url}") 

if redis_url:
    print(f"Found Redis URL from environment variable")
else:
    print("No Redis URL found in environment, using localhost")
    redis_url = 'redis://localhost:6379'

print(f"Connecting to Redis at: {redis_url[:8]}...") 

if redis_url:
    print(f"Found Redis URL from environment variable")
else:
    print("No Redis URL found in environment, using localhost")
    redis_url = 'redis://localhost:6379'

try:
    # Connect using the Redis URL
    print("Attempting to connect to Redis...")
    redis_client = redis.from_url(redis_url, decode_responses=True)
    # Test the connection
    redis_client.ping()
    print("Successfully connected to Redis!")
except Exception as e:
    print(f"Failed to connect to Redis: {str(e)}")

# Connect to Redis
# redis_host = os.environ.get('REDIS_HOST', 'localhost')
# redis_port = int(os.environ.get('REDIS_PORT', 6379))    
# redis_client = redis.Redis(host=redis_host, port=redis_port)

@app.route('/')
def home():
    return 'Hello, World!'


@app.route('/get_user_info')
def get_user_info():
    params = request.args
    phone_number = params.get('phone')
    print(f"Phone number received: {phone_number}")
    if not phone_number:
        return jsonify({'error': 'Phone number is required'}), 400
    
     # Construct key and look up user
    phone_key = f"phone:{phone_number}"
    print(f"Looking up Redis key: {phone_key}")

    user_id = redis_client.get(phone_key)
    print(f"Redis lookup result for {phone_key}: {user_id}")
    
    if not user_id:
        print(f"No user ID found for phone: {phone_number}")
        return jsonify({'error': 'User not found'}), 404
            

    # Check if user exists in Redis
    user_info = get_user_by_phone(str(phone_number))

    if user_info:
        # decoded_info = {k.decode('utf-8'): v.decode('utf-8') for k, v in user_info.items()}
        print(f"Decoded info: {user_info}")
        # return jsonify({'user_info': user_info.decode('utf-8'), }), 200
        return jsonify({'user_info': dict(user_info)}), 200
    else:
        return jsonify({'error': 'User not found'}), 404
    
def create_user(phone_number, user_data):

    # Generate a unique user ID (you could use UUID or incremental ID)
    user_id = f"user:{redis_client.incr('user:id:counter')}"

    # Store the user data as a hash
    redis_client.hset(
        user_id,
        mapping={
            "phone": phone_number,
            **user_data  # Spread any additional user data
        }
    )

    # Create phone number reference
    redis_client.set(f"phone:{phone_number}", user_id)

    return user_id

def get_user_by_phone(phone_number):
    """
    Retrieve user data using phone number
    """
    # First get the user ID using phone reference
    user_id = redis_client.get(f"phone:{phone_number}")
    
    if not user_id:
        return None
        
    # Then get the full user data
    return redis_client.hgetall(user_id)

@app.route('/test-redis', methods=['GET'])
def test_redis():
    try:
        # Try to ping Redis
        result = redis_client.ping()
        # Try to get Redis info
        info = redis_client.info()
        return jsonify({
            "redis_ping": result,
            "redis_status": "connected",
            "redis_info": {
                "version": info.get('redis_version'),
                "connected_clients": info.get('connected_clients'),
                "used_memory_human": info.get('used_memory_human')
            }
        })
    except Exception as e:
        return jsonify({
            "redis_status": "error",
            "error": str(e)
        }), 500

@app.route('/create-test-user', methods=['POST'])   
def create_test_user():
    try:
        # Example user data
        user_data = {
            'phone': '9259898099',
            'name': 'Erin',
            'mc_number': '98238829',
            'load_number': '12324',
            'email': 'erinkdelong@gmail.com'
        }
        
        # Generate user ID
        user_id = f"user:{redis_client.incr('user:id:counter')}"
        
        # Store user data
        redis_client.hset(user_id, mapping=user_data)
        
        # Create phone reference
        redis_client.set(f"phone:{user_data['phone']}", user_id)
        
        return jsonify({
            'message': 'User created',
            'user_id': user_id,
            'data': user_data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500 

@app.route('/edit_user_info', methods=['POST']) 
def edit_user_info():
    # Key for the user (phone number)
    phone_number = "9259898099"

    # Modify the existing hash fields
    # 1. Update the user's age (change to 35)
    # 2. Add a new field "address"
    redis_client.hset(phone_number, "pickup_number", "0987")
    return jsonify({'message': 'User info updated'}), 200
    

@app.route('/debug-redis', methods=['GET'])
def debug_redis():
    try:
        # Get all keys
        all_keys = redis_client.keys('*')
        
        # Initialize results
        result = {
            'all_keys': all_keys,
            'data_by_key': {}
        }
        
        # Check each key's type and get data accordingly
        for key in all_keys:
            key_type = redis_client.type(key)
            result['data_by_key'][key] = {
                'type': key_type,
                'value': None
            }
            
            try:
                if key_type == 'string':
                    result['data_by_key'][key]['value'] = redis_client.get(key)
                elif key_type == 'hash':
                    result['data_by_key'][key]['value'] = redis_client.hgetall(key)
                elif key_type == 'list':
                    result['data_by_key'][key]['value'] = redis_client.lrange(key, 0, -1)
                elif key_type == 'set':
                    result['data_by_key'][key]['value'] = list(redis_client.smembers(key))
            except Exception as e:
                result['data_by_key'][key]['error'] = str(e)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Add a simple key inspection endpoint
@app.route('/inspect-key/<key>', methods=['GET'])
def inspect_key(key):
    try:
        key_type = redis_client.type(key)
        result = {
            'key': key,
            'type': key_type,
            'value': None
        }
        
        if key_type == 'string':
            result['value'] = redis_client.get(key)
        elif key_type == 'hash':
            result['value'] = redis_client.hgetall(key)
        elif key_type == 'list':
            result['value'] = redis_client.lrange(key, 0, -1)
        elif key_type == 'set':
            result['value'] = list(redis_client.smembers(key))
            
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5001))  # Defaults to 5001 if PORT is not set
    app.run(host="0.0.0.0", port=port)

    user_data1 = {
        "name": "John Doe",
        "mc_number": "12345",
        "load_number": "67890",
        "email": "john.doe@example.com"
    }

    user_data2 = {
        "name": "Erin",
        "mc_number": "98238829",
        "load_number": "12324",
        "email": "erinkdelong@gmail.com"
    }

    user_data3 = {
        "name": "Ari",
        "mc_number": "237823",
        "load_number": "189891",
        "email": "ari@gmail.com"
    }

    # create_user("1234567890", user_data1)
    # create_user("9259898099", user_data2)
    # create_user("5108981234", user_data3)




