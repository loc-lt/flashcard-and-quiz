from constants.http_status_code import HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED, HTTP_409_CONFLICT
from flask import *
from flask import Blueprint, request, jsonify, current_app, session
from werkzeug.security import check_password_hash, generate_password_hash
from flask_jwt_extended import jwt_required, create_access_token, create_refresh_token, get_jwt_identity
from flasgger import swag_from
from database import *
from psycopg2 import sql
from error_handle import *
from auth_middleware import *
import bcrypt
import jwt
import traceback
import datetime
from utils.validators import validate_email, validate_name, validate_integer
from utils.database import get_db_connection

users = Blueprint("user", __name__, url_prefix="/api/v1/users")

# Extra functions
def check_exist(email):
    conn = None
    cursor = None

    try:
        # Create connection
        conn = get_db_connection()
        cursor = conn.cursor()

        # Query
        query = '''SELECT * FROM public."user" WHERE email = %s'''
        
        # Check email is registered or not
        cursor.execute(query, (email,))
        user_list = cursor.fetchall()
        
        if len(user_list) > 0:
            return True
        return False
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error: {error}")
        return False
    finally:
        # Close connection
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def add_user(email, password, name, role):
    conn = None
    cursor = None

    try:
        # Create connection
        conn = get_db_connection
        cursor = conn.cursor()

        # Insert user information to table "user" 
        query = sql.SQL('''INSERT INTO public."user"(name, email, password, role, created_at, updated_at, is_deleted) VALUES (%s, %s, %s, %s, %s, %s, %s)''')
        cursor.execute(query, (name, email, password, role, datetime.datetime.now(), datetime.datetime.now(), False))
        conn.commit()

        return True
    except (Exception, psycopg2.IntegrityError) as error:
        print(f"Error: {error}")
        Systemp_log(traceback.format_exc(), "add_user").append_new_line()
        conn.rollback()  # Rollback in case of error
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
# CREATE -> if create a user has already deleted?
@users.post("")
@swag_from("./docs/users/create.yaml")
def create_user():
    try:
        # Get data from request
        name = request.json['name']
        email = request.json['email']
        role = request.json['role']
        password = request.json['password']

        # Validate inputs
        if not (name or email or role or password):
            ret = {
                    'status': False,
                    'message':'Please fill in all information!'
                }
            return jsonify(ret), HTTP_400_BAD_REQUEST
        
        if not validate_email(email):
            ret = {
                    'status': False,
                    'message':'Invalid email!'
                }
            return jsonify(ret), HTTP_400_BAD_REQUEST
        
        if not validate_name(name):
            ret = {
                    'status': False,
                    'message':'Name contains special characters!'
                }
            return jsonify(ret), HTTP_400_BAD_REQUEST
        
        if not validate_integer(role):
            ret = {
                    'status': False,
                    'message':'Value is not an integer!'
                }
            return jsonify(ret), HTTP_400_BAD_REQUEST

        # Check if the email is used to register another account?
        if check_exist(email):
            ret = {
                    'status': False,
                    'message':'This email already registered!'
                }
            return jsonify(ret), HTTP_400_BAD_REQUEST

        # Converting password to array of bytes 
        bytes = password.encode('utf-8') 

        # Generating the salt 
        salt = bcrypt.gensalt() 
        
        # Hashing the password 
        hash_password = bcrypt.hashpw(bytes, salt)

        if add_user(email, hash_password.decode('utf-8'), name, role):
            ret = {
                    'status': True,
                    'message':'Register new account successfully!'
                }
            return jsonify(ret), HTTP_200_OK
        
        ret = {
                'status': False,
                'message':'Server error or run query not successfully!'
            }
        
        return jsonify(ret), HTTP_500_INTERNAL_SERVER_ERROR
    except Exception as e:
        ret = {
            'status': False,
            'message': str(e)
        }
        return jsonify(ret), HTTP_500_INTERNAL_SERVER_ERROR

# READ
@users.get("")
@swag_from("./docs/users/users_infor.yaml")
@token_required
def get_users_infor():
    conn = None
    cursor = None

    try:
        # Create connection
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get all user in table "user"
        cursor.execute('''select email, name, role from public."user"''')
        all_users = cursor.fetchall()
        
        # If has not any user
        if all_users is None:
            ret = {
                'status':False,
                'message':'Run query not successfully!'
            }
            return jsonify(ret), HTTP_500_INTERNAL_SERVER_ERROR
        
        ret = {
                'status':True,
                'message':'Get all users information succesfully!',
                'data':[]
            }
        
        if len(all_users) == 0:
            ret['data'] = None
            return jsonify(ret), HTTP_200_OK
        
        for item in all_users:
            ret['data'].append({
                'email':item[0].strip(),
                'name':item[1],
                'role':item[2]
            })
            
        return jsonify(ret)
    except Exception as e:
        ret = {
            'status': False,
            'message': str(e)
        }
        Systemp_log(traceback.format_exc(), "get_users_infor").append_new_line()
        return jsonify(ret), HTTP_500_INTERNAL_SERVER_ERROR
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@users.post("/login")
@swag_from("./docs/users/login.yaml")
def login():
    conn = None
    cursor = None
    try:
        # Create connection
        conn = get_db_connection()
        cursor = conn.cursor()

        # Processing data from request 
        email = request.json["email"]
        password = request.json['password']

        # Validate inputs
        if not validate_email(email):
            ret = {
                    'status': False,
                    'message':'Invalid email!'
                }
            return jsonify(ret), HTTP_400_BAD_REQUEST

        # If email has not registered yet
        if not check_exist(email):
            ret = {
                    'status': False,
                    'message':'Email or password is incorrect!'
                }
            return jsonify(ret), HTTP_400_BAD_REQUEST

        # Encoding user password
        hash_password = password.encode('utf-8')

        # Get hash of password from database by email
        query = sql.SQL('''select email, password, role from public."user" where email = %s''')
        cursor.execute(query, (email, ))
        hash_pw_role = cursor.fetchone()

        if len(hash_pw_role) == 0:
            return jsonify({
                            'status':False,
                            'message':'Username or password is incorrect!'
                            }), HTTP_400_BAD_REQUEST 

        # checking password
        result = bcrypt.checkpw(hash_password, hash_pw_role[1].encode('utf-8'))
        
        if result:
            session['logged_in'] = True

            token = jwt.encode({
                'email': hash_pw_role[0],
                'role': hash_pw_role[2],
                'expiration': (datetime.datetime.now() + datetime.timedelta(hours=12)).timestamp()
            }, current_app.config['SECRET_KEY'], algorithm="HS256")

            # Lưu token vào Redis
            redis_client.set(hash_pw_role[0], token)
            
            print(token)
            print(redis_client.keys())

            ret = {
                    'status': True,
                    'message':'Login successfully!',
                    'data': token
                }
            
            return jsonify(ret), HTTP_200_OK

        return jsonify({
                        'status':False,
                        'message':'Username or password is incorrect!'
                        }), HTTP_400_BAD_REQUEST
    except Exception as e:
        ret = {
            'status': False,
            'message': str(e)
        }
        Systemp_log(traceback.format_exc(), "login").append_new_line()
        return jsonify(ret), HTTP_500_INTERNAL_SERVER_ERROR
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Hàm logout
@users.post("/logout")
@swag_from("./docs/users/logout.yaml")
def logout():
    try:
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing!'}), HTTP_401_UNAUTHORIZED

        # Giải mã token để lấy username
        decoded_token = jwt.decode(token.split(' ')[1], current_app.config['SECRET_KEY'], algorithms=["HS256"])
        email = decoded_token['email']

        # Xóa token từ Redis
        redis_client.delete(email)

        # Xóa session
        session.pop('logged_in', None)

        ret = {
            'status': True,
            'message': 'Logout successfully!'
        }

        return jsonify(ret), HTTP_200_OK
    except Exception as e:
        ret = {
            'status': False,
            'message': str(e)
        }
        Systemp_log(traceback.format_exc(), "logout").append_new_line()
        return jsonify(ret), HTTP_500_INTERNAL_SERVER_ERROR