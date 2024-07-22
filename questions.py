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
from utils.validators import validate_email, validate_name, validate_integer, is_boolean, is_valid_uuid, is_valid_question_type, count_correct_answers
from utils.database import get_db_connection 

questions = Blueprint("questions", __name__, url_prefix="/api/v1/questions")

# CREATE
@questions.post("")
@swag_from("./docs/questions/create.yaml")
@user_token_required
@set_id_required
def create_question(user_id, set_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get data from request
        content = request.json['content']
        type = request.json['type']
        list_answers = request.json['list_answers']

        # Check if user_id or set_id is not uuid type
        if not is_valid_uuid(user_id) or not is_valid_uuid(set_id):
            ret = {
                    'status': False,
                    'message':'Type of user_id and set_id must is uuid!'
                }
            return jsonify(ret), HTTP_400_BAD_REQUEST  
        
        # Check if the description is filled in or not
        if not content:
            ret = {
                    'status': False,
                    'message':'Please fill in content of question!'
                }
            return jsonify(ret), HTTP_400_BAD_REQUEST
        
        # Checks if type is one of three values: Text_Fill, Multiple_Choice, Checkboxes
        if not is_valid_question_type(type):
            ret = {
                    'status': False,
                    'message':'Invalid type of question!'
                }
            return jsonify(ret), HTTP_400_BAD_REQUEST
        
        # Check if invalid answers with each question type
        if type == 'Text_Fill':
            if len(list_answers) != 1:
                ret = {
                        'status': False,
                        'message':'Text file question has only a answer!'
                    }
                return jsonify(ret), HTTP_400_BAD_REQUEST
            elif count_correct_answers(list_answers) != 1:
                ret = {
                        'status': False,
                        'message':'Answer of text fill question must is correct!'
                    }
                return jsonify(ret), HTTP_400_BAD_REQUEST
        elif type == 'Multiple_Choice':
            if len(list_answers) < 2:
                ret = {
                        'status': False,
                        'message':'Multiple choice question has more than a answer!'
                    }
                return jsonify(ret), HTTP_400_BAD_REQUEST
            elif count_correct_answers(list_answers) != 1:     
                ret = {
                        'status': False,
                        'message':'Multiple choice question has only a correct answer!'
                    }
                return jsonify(ret), HTTP_400_BAD_REQUEST
        elif type == 'Checkboxes':
            if len(list_answers) == count_correct_answers(list_answers):
                ret = {
                    'status': False,
                    'message': "Amount of correct answers must less than amount of answers!"
                }
                return jsonify(ret), HTTP_400_BAD_REQUEST
            elif len(list_answers) < 3:
                ret = {
                        'status': False,
                        'message':'Checkboxes question has more than two answer!'
                    }
                return jsonify(ret), HTTP_400_BAD_REQUEST
            elif count_correct_answers(list_answers) < 2:
                ret = {
                        'status': False,
                        'message':'Checkboxes question has more than a correct answer!'
                    }
                return jsonify(ret), HTTP_400_BAD_REQUEST
        
        # Check if user is deleted
        query1 = sql.SQL('''select is_deleted from public."user" where id = %s''')
        cursor.execute(query1, (user_id, ))
        
        user_is_deleted = cursor.fetchone()
        if not user_is_deleted:
            ret = {
                    'status': False,
                    'message':'This user has been deleted!'
                }
            return jsonify(ret), HTTP_400_BAD_REQUEST
        
        # Check if is not owner or set is deleted
        query2 = sql.SQL('''select is_deleted from public.set where id = %s and user_id = %s''')
        cursor.execute(query2, (set_id, user_id))
        
        set_is_deleted = cursor.fetchone()

        if len(set_is_deleted) == 0:
            ret = {
                    'status': False,
                    'message':'Sorry, permission denied!'
                }
            return jsonify(ret), HTTP_403_FORBIDDEN
         
        if not set_is_deleted:
            ret = {
                    'status': False,
                    'message':'This set has been deleted!'
                }
            return jsonify(ret), HTTP_400_BAD_REQUEST

        # Create new questions
        query3 = sql.SQL('''insert into public.question (content, type, set_id, created_at, updated_at, is_deleted) 
                        values (%s, %s, %s, %s, %s, %s) RETURNING id''')
        cursor.execute(query3, (content, type, set_id, datetime.datetime.now(), datetime.datetime.now(), False))
        question_id = cursor.fetchone()[0]

        # Create answers of this question
        query4 = sql.SQL('''insert into public.answer (content, is_correct, question_id, created_at, updated_at, is_deleted)
                         values (%s, %s, %s, %s, %s, %s)''')
        for answer in list_answers:
            cursor.execute(query4, (answer['content'], answer['is_correct'], question_id, datetime.datetime.now(), datetime.datetime.now(), False))
        conn.commit()
        
        # Return response
        ret = {
                'status': True,
                'message':'Create new question successfully!'
            }
        
        return jsonify(ret), HTTP_200_OK
    except Exception as e:
        ret = {
            'status': False,
            'message': str(e)
        }
        Systemp_log(traceback.format_exc(), "create_new_question").append_new_line()
        return jsonify(ret), HTTP_500_INTERNAL_SERVER_ERROR
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@questions.delete("/<string:question_id>")
@swag_from("./docs/questions/delete.yaml")
@user_token_required
@set_id_required
def delete_set(user_id, set_id, question_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if set_id or question_id is filled in or not
        if not set_id or not question_id:
            ret = {
                    'status': False,
                    'message':'Please fill in set_id and question_id!'
                }
            return jsonify(ret), HTTP_400_BAD_REQUEST 

        # Check if set_id is uuid type or not
        if not is_valid_uuid(set_id) or not is_valid_uuid(question_id):
            ret = {
                    'status': False,
                    'message':'Type of set_id and question_id must is uuid!'
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
        
        # Update question information
        query3 = sql.SQL('''update public.question set is_deleted = %s where id = %s''')
        
        cursor.execute(query3, (True, question_id))
        conn.commit()

        # Return response
        ret = {
                'status': True,
                'message':'Delete question successfully!'
            }
        
        return jsonify(ret), HTTP_200_OK
    except Exception as e:
        ret = {
            'status': False,
            'message': str(e)
        }
        Systemp_log(traceback.format_exc(), "delete_question").append_new_line()
        return jsonify(ret), HTTP_500_INTERNAL_SERVER_ERROR
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()