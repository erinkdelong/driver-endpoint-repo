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
# This lets us add a pickup number to a load number
def edit_user_info():
    try:
        phone = "9259898099"
        load_number = "12324"  # This is the load number from your user data
        pickup_number = "0987"
        
        # Create a key for load-pickup mapping
        load_key = f"load:{load_number}"
        
        # Store the pickup number associated with the load number
        redis_client.hset(load_key, "pickup_number", pickup_number)
        
        # Get the updated info to return
        load_info = redis_client.hgetall(load_key)
        
        return jsonify({
            'message': 'Load info updated',
            'load_number': load_number,
            'load_info': load_info
        }), 200
    except Exception as e:
        print(f"Error updating load info: {str(e)}")
        return jsonify({'error': str(e)}), 500
    
@app.route('/delete_all_users', methods=['DELETE'])
def delete_all_users():
    try:
        # Get all user and phone keys
        user_keys = redis_client.keys('user:*')
        phone_keys = redis_client.keys('phone:*')
        load_keys = redis_client.keys('load:*')
        
        # Delete all keys
        for key in user_keys + phone_keys + load_keys:
            redis_client.delete(key)
        
        return jsonify({
            'message': 'All users deleted',
            'users_deleted': len(user_keys),
            'phone_refs_deleted': len(phone_keys),
            'load_refs_deleted': len(load_keys)
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

@app.route('/cleanup', methods=['DELETE'])
def cleanup():
    try:
        # Delete the specific key
        redis_client.delete("9259898099")
        
        # Verify deletion
        all_keys = redis_client.keys('*')
        
        return jsonify({
            'message': 'Cleanup completed',
            'remaining_keys': all_keys
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

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
    

@app.route('/get_pickup_number', methods=['GET'])
def get_pickup_number():
    try:
        phone_number = request.args.get('phone')
        if not phone_number:
            return jsonify({'error': 'Phone number is required'}), 400

        # First get user info to get their load number
        user_id = redis_client.get(f"phone:{phone_number}")
        if not user_id:
            return jsonify({'error': 'User not found'}), 404

        # Get user's load number
        user_info = redis_client.hgetall(user_id)
        load_number = user_info.get('load_number')
        if not load_number:
            return jsonify({'error': 'No load number found for user'}), 404

        # Get pickup number associated with the load
        pickup_number = redis_client.hget(f"load:{load_number}", "pickup_number")
        if not pickup_number:
            return jsonify({'error': 'No pickup number found for this load'}), 404

        return jsonify({
            'phone_number': phone_number,
            'load_number': load_number,
            'pickup_number': pickup_number
        }), 200
    except Exception as e:
        print(f"Error getting pickup number: {str(e)}")
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




