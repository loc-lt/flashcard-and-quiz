import jwt
from functools import wraps
from flask import request
from flask.json import jsonify
from flask import current_app 
from fakeredis import FakeStrictRedis
from constants.http_status_code import *
from psycopg2 import sql

from error_handle import *

from utils.database import *
from utils.validators import *

# Connect to redis server
redis_client = FakeStrictRedis()

def token_required(func):
    @wraps(func)
    def decorated(*args, **kwargs):
        # Get token from request.header
        token = None
        if "Authorization" in request.headers:
            token = request.headers["Authorization"].split(" ")[1]
        
        # Check whether token exist or not
        if not token:
            ret = {
                'status':False,
                'message':'Sorry, token is missing!'
            }
            return jsonify(ret), HTTP_401_UNAUTHORIZED

        if len(token.split('.')) == 1:
            ret = {
                'status':False,
                'message':'Sorry, invalid token!'
            }
            return jsonify(ret), HTTP_401_UNAUTHORIZED

        try:
            payload = jwt.decode(token, current_app.config['SECRET_KEY'],algorithms=["HS256"])
        except Exception as e:
            ret = {
                'status':False,
                'message': 'Sorry, token not exist!',
                'error': e
            }
            return jsonify(ret), HTTP_401_UNAUTHORIZED 

        # Print payload after decode to test
        print(payload)
        
        # Check whether payload after decode is none or not 
        if payload is not None:
            if datetime.datetime.now().timestamp() <= payload['expiration']:
                # Return func with input data
                return func(*args, **kwargs)
            elif datetime.datetime.now().timestamp() > payload['expiration']:
                ret = {
                    'status':False,
                    'message':'Sorry, token expired!'
                }
                return jsonify(ret), HTTP_401_UNAUTHORIZED
            else:
                keys = redis_client.keys('*')
            
                # Get value for each key
                data = {}

                for key in keys:
                    data[key.decode('utf-8')] = redis_client.get(key).decode('utf-8')

                if token not in data.values():
                    ret = {
                        'status':False,
                        'message':'Sorry, token is not exist!'
                    }
                    return jsonify(ret),403
        else:
            ret = {
                'status':False,
                'message':'Sorry, invalid token!'
            }
            return jsonify(ret), HTTP_401_UNAUTHORIZED
        
    return decorated

def user_token_required(func):
    @wraps(func)
    def decorated(*args, **kwargs):
        # Get token from request.header
        token = None
        if "Authorization" in request.headers:
            token = request.headers["Authorization"].split(" ")[1]
        
        # Check whether token exist or not
        if not token:
            ret = {
                'status':False,
                'message':'Sorry, token is missing!'
            }
            return jsonify(ret), HTTP_401_UNAUTHORIZED

        if len(token.split('.')) == 1:
            ret = {
                'status':False,
                'message':'Sorry, invalid token!'
            }
            return jsonify(ret), HTTP_401_UNAUTHORIZED

        try:
            payload = jwt.decode(token, current_app.config['SECRET_KEY'],algorithms=["HS256"])
        except Exception as e:
            ret = {
                'status':False,
                'message': 'Sorry, token not exist!',
                'error': e
            }
            return jsonify(ret), HTTP_401_UNAUTHORIZED 

        # Print payload after decode to test
        print(payload)
        
        # Check whether payload after decode is none or not 
        if payload is not None:
            if datetime.datetime.now().timestamp() <= payload['expiration']:
                # Thêm user_id để trả về cho hàm
                conn = get_db_connection()
                cursor = conn.cursor()

                query = sql.SQL('''select id from public."user" where email = %s''')
                cursor.execute(query, (payload['email'], ))
                
                user_id = cursor.fetchone()

                cursor.close()
                conn.close()

                # Return func with input data
                return func(*args, **kwargs, user_id = user_id[0])
            elif datetime.datetime.now().timestamp() > payload['expiration']:
                ret = {
                    'status':False,
                    'message':'Sorry, token expired!'
                }
                return jsonify(ret), HTTP_401_UNAUTHORIZED
            else:
                keys = redis_client.keys('*')
            
                # Get value for each key
                data = {}

                for key in keys:
                    data[key.decode('utf-8')] = redis_client.get(key).decode('utf-8')

                if token not in data.values():
                    ret = {
                        'status':False,
                        'message':'Sorry, token is not exist!'
                    }
                    return jsonify(ret),403
        else:
            ret = {
                'status':False,
                'message':'Sorry, invalid token!'
            }
            return jsonify(ret), HTTP_401_UNAUTHORIZED
        
    return decorated

def set_id_required(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        try:
            # Get set_id from request
            set_id = request.json['set_id']

            # Check if type of set_id is not uuid
            if not set_id or not is_valid_uuid(set_id):
                return jsonify({
                    'status': False, 
                    'message': 'Invalid or missing set_id!'
                    }), HTTP_400_BAD_REQUEST
            
            return func(*args, **kwargs, set_id = set_id)
        except Exception as e:
            return jsonify({
                'status': False, 
                'message': str(e)
                }), HTTP_500_INTERNAL_SERVER_ERROR
    
    return decorated_function