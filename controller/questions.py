from constants.http_status_code import *
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

from utils.validators import is_valid_uuid, is_valid_question_type
from utils.database import get_db_connection 

questions = Blueprint("questions", __name__, url_prefix="/api/v1")

# CREATE
@questions.post("/questions")
@swag_from("../docs/questions/create.yaml")
@user_token_required
@set_id_required
def create_question(user_id, set_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get content from request (required)
        if 'content' not in request.json:
            ret = {
                    'status': False,
                    'message':'Please fill out content field!'
                }
            return jsonify(ret), HTTP_400_BAD_REQUEST  
        content = request.json['content']

        # Validate name
        if not is_valid_uuid(user_id) or not is_valid_uuid(set_id):
            ret = {
                    'status': False,
                    'message':'Type of user_id and set_id must is uuid!'
                }
            return jsonify(ret), HTTP_400_BAD_REQUEST  

        # Get type from request (required)
        if 'type' not in request.json:
            ret = {
                    'status': False,
                    'message':'Please fill out type field!'
                }
            return jsonify(ret), HTTP_400_BAD_REQUEST  
        type = request.json['type']

        # Checks if type is one of three values: Text_Fill, Multiple_Choice, Checkboxes
        if not is_valid_question_type(type):
            ret = {
                    'status': False,
                    'message':'Invalid type of question!'
                }
            return jsonify(ret), HTTP_400_BAD_REQUEST

        # Get name from request (required)
        if 'answers' not in request.json:
            ret = {
                    'status': False,
                    'message':'Please fill out answer list!'
                }
            return jsonify(ret), HTTP_400_BAD_REQUEST  
        list_answers = request.json['answers']

        # Validate question and answers
        validation_error = validate_question_and_answers(type, list_answers)
        if validation_error:
            message, status_code = validation_error
            return jsonify({'status': False, 'message': message}), status_code
        
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
                        values (%s, %s, %s, %s, %s, %s) returning id;''')
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

@questions.delete("/sets/<string:set_id>/questions/<string:question_id>")
@swag_from("../docs/questions/delete.yaml")
@user_token_required
def delete_set(user_id, set_id, question_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor() 

        # Check if set_id and question_id is uuid type or not
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
                    'message':'Set owner has been deleted!'
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
        
        # Check if set don't include question
        query3 = sql.SQL('''select * from public.question where set_id = %s and id = %s''')
        cursor.execute(query3, (set_id, question_id, ))

        check_set_question = cursor.fetchone()
        if check_set_question is None or len(check_set_question) == 0:
            ret = {
                    'status': False,
                    'message':'Sorry, set do not include question!'
                }
            return jsonify(ret), HTTP_400_BAD_REQUEST

        # Update question information
        query4 = sql.SQL('''update public.question set is_deleted = %s where id = %s''')
        
        cursor.execute(query4, (True, question_id))
        conn.commit()

        # Return response
        ret = {
                'status': True,
                'message':'Delete question successfully!'
            }
        
        return jsonify(ret), HTTP_204_NO_CONTENT
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

@questions.put("/sets/<string:set_id>/questions/<string:question_id>")
@swag_from("../docs/questions/update.yaml")
@user_token_required
def update_question(user_id, set_id, question_id):
    try:
        # Create connection
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if set_id and question_id is uuid type or not
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
        
        # Check if set don't include question
        query3 = sql.SQL('''select * from public.question where set_id = %s and id = %s''')
        cursor.execute(query3, (set_id, question_id, ))

        check_set_question = cursor.fetchone()
        if check_set_question is None or len(check_set_question) == 0:
            ret = {
                    'status': False,
                    'message':'Sorry, set do not include question!'
                }
            return jsonify(ret), HTTP_400_BAD_REQUEST

        # Get data from request
        content = request.json['content']
        question_type = request.json['type']
        list_answers_to_delete = request.json['delete_answers']
        list_answers_to_add = request.json['add_answers']
        list_answers_to_update = request.json['update_answers']

        # Validate question and answers
        all_answers = list_answers_to_add + list_answers_to_update
        validation_error = validate_question_and_answers(question_type, all_answers)
        if validation_error:
            message, status_code = validation_error
            return jsonify({
                'status': False, 
                'message': message
            }), status_code

        # Start transaction
        cursor.execute('BEGIN')

        # Delete answers
        for answer_id in list_answers_to_delete:
            cursor.execute(
                '''update public.answer set is_deleted = %s where id = %s''',
                (True, answer_id)
            )

        # Add new answers
        for answer in list_answers_to_add:
            cursor.execute(
                '''insert into public.answer (content, is_correct, question_id, created_at, updated_at, is_deleted)
                   values (%s, %s, %s, %s, %s, %s)''',
                (answer['content'], answer['is_correct'], question_id, datetime.datetime.now(), datetime.datetime.now(), False)
            )

        # Update existing answers
        for answer in list_answers_to_update:
            cursor.execute(
                '''update public.answer set content = %s, is_correct = %s, updated_at = %s 
                   where id = %s and question_id = %s''',
                (answer['content'], answer['is_correct'], datetime.datetime.now(), answer['id'], question_id)
            )

        # Update question content and type if needed
        cursor.execute(
            '''update public.question set content = %s, type = %s, updated_at = %s 
               where id = %s and set_id = %s''',
            (content, question_type, datetime.datetime.now(), question_id, set_id)
        )

        # Commit transaction
        conn.commit()

        # Return response
        return jsonify({'status': True, 'message': 'Update question successfully!'}), HTTP_200_OK
    except Exception as e:
        if conn:
            # Rollback if update failed
            conn.rollback()
        return jsonify({'status': False, 'message': str(e)}), HTTP_500_INTERNAL_SERVER_ERROR
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# READ
@questions.get("questions/<string:question_id>")
@swag_from("../docs/questions/all_answers.yaml")
@user_token_required
@set_id_required
def get_all_questions_of_set(user_id, question_id):
    try:
        # Create connection
        conn = get_db_connection()
        cursor = conn.cursor()  

        # Check if set_id is uuid type or not
        if not is_valid_uuid(question_id):
            ret = {
                    'status': False,
                    'message':'Type of question_id must is uuid!'
                }
            return jsonify(ret), HTTP_400_BAD_REQUEST  
        
        # Check if user is deleted
        query = sql.SQL('''select is_deleted from public."user" where id = %s''')
        cursor.execute(query, (user_id, ))
        is_deleted = cursor.fetchone()

        if not is_deleted:
            ret = {
                    'status': False,
                    'message':'Owner of questions has been deleted!'
                }
            return jsonify(ret), HTTP_400_BAD_REQUEST
        
        # Check if set is not exist or is deleted 
        query1 = sql.SQL('''select is_deleted from public.question where id = %s''')
        cursor.execute(query1, (question_id, ))

        check_deleted = cursor.fetchone()

        if check_deleted is None:
            ret = {
                'status':False,
                'message':'This question is not exist!'
            }
            return jsonify(ret), HTTP_400_BAD_REQUEST
        
        if check_deleted[0]: 
            ret = {
                'status':False,
                'message':'This questions has been deleted!'
            }
            return jsonify(ret), HTTP_400_BAD_REQUEST
        
        # Check if user isn't owner of questions
        query2 = sql.SQL('''select * 
                         from public."user" a
                         join public.set b
                         on a.id = b.user_id and a.id = %s
                         join public.question c
                         on b.id = c.set_id and c.id = %s''')
        cursor.execute(query2, (user_id, question_id, ))

        check_question_user = cursor.fetchone()
        
        if check_question_user is None or len(check_question_user) == 0:
            ret = {
                    'status': False,
                    'message':'Sorry, permission denied!'
                }
            return jsonify(ret), HTTP_400_BAD_REQUEST
        
        ret = {
                'status': True,
                'message':'Get all answers successfully!',
                'data': {}
            }
            
        # Get all questions and answers
        query3 = sql.SQL('''select a.content, b.content, b.is_correct  
                         from public.question a
                         join public.answer b 
                         on a.id = b.question_id and b.question_id = %s and b.is_deleted != true
                         ''')
        
        cursor.execute(query3, (question_id, ))
        questions_answers = cursor.fetchall()

        # Get content of question and its answers
        ret['data']['question_content'] = questions_answers[0][0]
        ret['data']['answers'] = []

        # Get all answers
        for item in questions_answers:
            ret['data']['answers'].append({'answer_content': item[1], 'is_correct': item[2]})

        return jsonify(ret), HTTP_200_OK
    except Exception as e:
        ret = {
            'status': False,
            'message': str(e)
        }
        Systemp_log(traceback.format_exc(), "get_all_answers_of_question").append_new_line()
        return jsonify(ret), HTTP_500_INTERNAL_SERVER_ERROR
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()