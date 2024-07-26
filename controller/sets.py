from constants.http_status_code import HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED, HTTP_409_CONFLICT
from flask import *
from flask import Blueprint, request, jsonify, current_app, session
from werkzeug.security import check_password_hash, generate_password_hash
from flask_jwt_extended import jwt_required, create_access_token, create_refresh_token, get_jwt_identity
from flasgger import swag_from
from database import *
from psycopg2 import sql
from error_handle import *
from controller.auth_middleware import *
import traceback
import datetime
from utils.validators import validate_email, validate_name, validate_integer, is_boolean, is_valid_uuid
from utils.database import get_db_connection 

sets = Blueprint("sets", __name__, url_prefix="/api/v1/sets")

# CREATE
@sets.post("")
@swag_from("../docs/sets/create.yaml")
@user_token_required
def create_set(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get data from request
        description = request.json['description']

        # Check if the description is filled in or not
        if not description:
            ret = {
                    'status': False,
                    'message':'Please fill in description!'
                }
            return jsonify(ret), HTTP_400_BAD_REQUEST
        
        # Check if user is deleted
        query1 = sql.SQL('''select is_deleted from public."user" where id = %s''')
        cursor.execute(query1, (user_id, ))
        
        is_deleted = cursor.fetchone()
        if not is_deleted:
            ret = {
                    'status': False,
                    'message':'This user has been deleted!'
                }
            return jsonify(ret), HTTP_400_BAD_REQUEST

        # Save new set
        query2 = sql.SQL('''insert into public.set (user_id, created_at, updated_at, is_deleted, public_or_not, description) 
                        values (%s, %s, %s, %s, %s, %s)''')
        cursor.execute(query2, (user_id, datetime.datetime.now(), datetime.datetime.now(), False, False, description))
        conn.commit()

        # Return response
        ret = {
                'status': True,
                'message':'Create new set successfully!'
            }
        
        return jsonify(ret), HTTP_200_OK
    except Exception as e:
        ret = {
            'status': False,
            'message': str(e)
        }
        Systemp_log(traceback.format_exc(), "create_new_set").append_new_line()
        return jsonify(ret), HTTP_500_INTERNAL_SERVER_ERROR
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@sets.put("")
@swag_from("../docs/sets/update.yaml")
@user_token_required
def update_set(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get data from request
        set_id = request.json['set_id']
        description = request.json['description']

        # Check if set_id is filled in or not
        if not set_id:
            ret = {
                    'status': False,
                    'message':'Please fill in set_id!'
                }
            return jsonify(ret), HTTP_400_BAD_REQUEST
        
        # Check if set_id is uuid type or not
        if not is_valid_uuid(set_id):
            ret = {
                    'status': False,
                    'message':'Type of set_id must is uuid!'
                }
            return jsonify(ret), HTTP_400_BAD_REQUEST
        
        # Check if the description is empty
        if len(description) == 0:
            ret = {
                    'status': False,
                    'message':'Please fill in description!'
                }
            return jsonify(ret), HTTP_400_BAD_REQUEST     

        # Check if user is deleted
        query1 = sql.SQL('''select is_deleted from public."user" where id = %s''')
        cursor.execute(query1, (user_id, ))
        
        is_deleted = cursor.fetchone()
        if not is_deleted:
            ret = {
                    'status': False,
                    'message':'Owner of set has been deleted!'
                }
            return jsonify(ret), HTTP_400_BAD_REQUEST
        
        # Check if user isn't owner of this set
        query2 = sql.SQL('''select * from public.set where user_id = %s and id = %s''')
        cursor.execute(query2, (user_id, set_id))

        check_owner = cursor.fetchone()
        if check_owner is not None and len(check_owner) == 0:
            ret = {
                    'status': False,
                    'message':'Sorry, permission denied!'
                }
            return jsonify(ret), HTTP_403_FORBIDDEN
        
        # Update set information
        query3 = sql.SQL('''update public.set set description = %s, updated_at = %s where id = %s''')
        cursor.execute(query3, (description, datetime.datetime.now(), set_id))
        conn.commit()

        # Return response
        ret = {
                'status': True,
                'message':'Update set successfully!'
            }
        
        return jsonify(ret), HTTP_200_OK
    except Exception as e:
        ret = {
            'status': False,
            'message': str(e)
        }
        Systemp_log(traceback.format_exc(), "create_new_set").append_new_line()
        return jsonify(ret), HTTP_500_INTERNAL_SERVER_ERROR
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@sets.delete("/<string:set_id>")
@swag_from("../docs/sets/delete.yaml")
@user_token_required
def delete_set(set_id, user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if set_id is filled in or not
        if not set_id:
            ret = {
                    'status': False,
                    'message':'Please fill in set_id!'
                }
            return jsonify(ret), HTTP_400_BAD_REQUEST 

        # Check if set_id is uuid type or not
        if not is_valid_uuid(set_id):
            ret = {
                    'status': False,
                    'message':'Type of set_id must is uuid!'
                }
            return jsonify(ret), HTTP_400_BAD_REQUEST  

        # Check if user is deleted
        query1 = sql.SQL('''select is_deleted from public."user" where id = %s''')
        cursor.execute(query1, (user_id, ))
        
        is_deleted = cursor.fetchone()
        if not is_deleted:
            ret = {
                    'status': False,
                    'message':'Owner of set has been deleted!'
                }
            return jsonify(ret), HTTP_400_BAD_REQUEST
        
        # Check if user isn't owner of this set
        query2 = sql.SQL('''select * from public.set where user_id = %s and id = %s''')
        cursor.execute(query2, (user_id, set_id))

        check_owner = cursor.fetchone()
        if check_owner is not None and len(check_owner) == 0:
            ret = {
                    'status': False,
                    'message':'Sorry, permission denied!'
                }
            return jsonify(ret), HTTP_403_FORBIDDEN
        
        # Update set information
        query3 = sql.SQL('''update public.set set is_deleted = %s where id = %s''')
        cursor.execute(query3, (True, set_id))
        conn.commit()

        # Return response
        ret = {
                'status': True,
                'message':'Delete set successfully!'
            }
        
        return jsonify(ret), HTTP_200_OK
    except Exception as e:
        ret = {
            'status': False,
            'message': str(e)
        }
        Systemp_log(traceback.format_exc(), "delete_new_set").append_new_line()
        return jsonify(ret), HTTP_500_INTERNAL_SERVER_ERROR
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# READ
@sets.get("/<string:set_id>")
@swag_from("../docs/sets/all_questions.yaml")
@user_token_required
def get_all_questions_of_set(user_id, set_id):
    try:
        # Create connection
        conn = get_db_connection()
        cursor = conn.cursor()  

        # Check if set_id is uuid type or not
        if not is_valid_uuid(set_id):
            ret = {
                    'status': False,
                    'message':'Type of set_id must is uuid!'
                }
            return jsonify(ret), HTTP_400_BAD_REQUEST  
        
        # Check if set is not exist or is deleted 
        query1 = sql.SQL('''select is_deleted from public.set where id = %s''')
        cursor.execute(query1, (set_id, ))

        check_deleted = cursor.fetchone()

        if check_deleted is None:
            ret = {
                'status':False,
                'message':'This set is not exist!'
            }
            return jsonify(ret), HTTP_400_BAD_REQUEST
        
        if check_deleted[0]: 
            ret = {
                'status':False,
                'message':'This set has been deleted!'
            }
            return jsonify(ret), HTTP_400_BAD_REQUEST
        
        # Check if user isn't owner of this set
        query2 = sql.SQL('''select * from public.set where user_id = %s and id = %s''')
        cursor.execute(query2, (user_id, set_id))

        check_owner = cursor.fetchone()
        if check_owner is not None and len(check_owner) == 0:
            ret = {
                    'status': False,
                    'message':'Sorry, permission denied!'
                }
            return jsonify(ret), HTTP_403_FORBIDDEN
        
        ret = {
                'status': True,
                'message':'Get all questions and answers successfully!',
                'data': {}
            }
            
        # Get all questions and answers
        query3 = sql.SQL('''select a.description, b.content, c.content, c.is_correct  
                         from public.set a 
                         join public.question b 
                         on a.id = b.set_id and b.set_id = %s and b.is_deleted != true
                         join public.answer c
                         on b.id = c.question_id and c.is_deleted != true
                         ''')
        
        cursor.execute(query3, (set_id, ))
        questions_answers = cursor.fetchall()

        # Get set's description
        ret['data']['description'] = questions_answers[0][0]

        # Initialize list of question
        ret['data']['questions'] = []

        # Get all questions and answers
        question_content = ''
        answers_infors = []

        print(len(questions_answers))

        for idx, item in enumerate(questions_answers):
            if question_content == '':
                question_content = item[1]
                answers_infors.append({'answer_content': item[2], 'is_correct': item[3]})
            elif item[1] != question_content:
                ret['data']['questions'].append({'question_content': question_content, 'answers': answers_infors})
                answers_infors = [{'question_content': item[2], 'is_correct': item[3]}]
                question_content = item[1]
            else:
                answers_infors.append({'answer_content': item[2], 'is_correct': item[3]})

            if idx == len(questions_answers) - 1:
                ret['data']['questions'].append({'question_content': question_content, 'answers': answers_infors})

        return jsonify(ret), HTTP_200_OK
    except Exception as e:
        ret = {
            'status': False,
            'message': str(e)
        }
        Systemp_log(traceback.format_exc(), "get_all_questions_of_set").append_new_line()
        return jsonify(ret), HTTP_500_INTERNAL_SERVER_ERROR
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()