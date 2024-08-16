from constants.http_status_code import *
from flask import *
from flask import Blueprint, request, jsonify, current_app, session
from werkzeug.security import check_password_hash, generate_password_hash
from flask_jwt_extended import jwtrequired, create_access_token, create_refresh_token, get_jwt_identity
from flasgger import swag_from
from database import *
from psycopg2 import sql
from error_handle import *
from controller.auth_middleware import *
import traceback
import datetime
from utils.validators import validate_email, validate_name, validate_integer, is_boolean, is_valid_uuid
from utils.database import get_db_connection

answers = Blueprint("answers", __name__, url_prefix="/api/v1")

# Vấn đề gặp phải, là khi thêm 1 câu trả lời đâu cần phải check là question đó có thỏa hay không. Có nên CRUD answer không? Nếu cần thì thật sự ko cần check
# CREATE
@answers.post("/answers")
@swag_from("../docs/answers/create.yaml")
@user_token_required
@set_id_required
@question_id_required
def create_answer(user_id, set_id, question_id):
    try:
        # Create connection
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if user is deleted
        query = sql.SQL('''select is_deleted from public."user" where id = %s''')
        cursor.execute(query, (user_id, ))
        
        user_deleted = cursor.fetchone()
        if user_deleted[0]:
            ret = {
                    'status': False,
                    'message':'Set owner has been deleted!'
                }
            return jsonify(ret), HTTP_400_BAD_REQUEST
        
        # Check if set is deleted or user isn't owner of set
        query1 = sql.SQL('''select * from public.set where id = %s and user_id = %s''')
        cursor.execute(query1, (set_id, user_id, ))
        check_set_user = cursor.fetchone()

        if check_set_user is None or len(check_set_user) == 0:
            ret = {
                'status': False,
                'message': 'User is not owner of question!'
            }
            return jsonify(ret), HTTP_400_BAD_REQUEST
        
        if check_set_user[4]:
            ret = {
                'status': False,
                'message': 'This set has been deleted!'
            }
            return jsonify(ret), HTTP_400_BAD_REQUEST
        
        # Check if set don't include question or question is deleted
        query2 = sql.SQL('''select * from public.question where id = %s and set_id = %s''')
        cursor.execute(query2, (question_id, set_id, ))
        check_question_set = cursor.fetchone()

        if check_question_set is None or len(check_question_set):
            ret = {
                'status': False,
                'message': 'Set do not include question!'
            }
            return jsonify(ret), HTTP_400_BAD_REQUEST
        
        if check_question_set[6]:
            ret = {
                'status': False,
                'message': 'This question has been deleted!'
            }

        ret = {
            'status': True, 
            'message': 'Create new answer successfully!' 
        }

        # Get content from request
        if 'content' not in request.json:
            ret = {
                'status': False,
                'message': 'Content is required!'
            }
        content = request.json['content']

        # Get is_correct from request
        if 'is_correct' not in request.json:
            ret = {
                'status': False,
                'message': 'Is_correct is required!'
            }
        is_correct = request.json['is_correct']

        # Get all answers of this question
        query3 = sql.SQL('''select content, is_correct from public.answer where question_id = %s''')
        cursor.execute(query3, (question_id, ))
        answers_of_question = cursor.fetchall()

        list_answers = []
        for item in answers_of_question:
            list_answers.append({
                'content': item[0],
                'is_correct': item[1]                
            })

        # Add this answer (want to create) to list_answers
        list_answers.append({
            'content': content,
            'is_correct': is_correct
        }) 

        # Validate question and answers
        validation_error = validate_question_and_answers(type, list_answers)
        if validation_error:
            message, status_code = validation_error
            return jsonify({'status': False, 'message': message}), status_code
        
        ret = {
            'status': True,
            'message': 'Create new answer successfully!' 
        }

        # Create new answer
        query4 = sql.SQL('''insert into public.answer (content, is_correct, question_id, created_at, updated_at, is_deleted) 
                         values (%s, %s, %s, %s, %s, %s) returning id;''')
        cursor.execute(query4, (content, is_correct, question_id, datetime.datetime.now(), datetime.datetime.now(), False))
    
        id_return = cursor.fetchone()
        ret['id'] = id_return[0]

        return jsonify(ret), HTTP_200_OK
    except Exception as e:
        ret = {
            'status': False,
            'message': str(e)
        }
        Systemp_log(traceback.format_exc(), "create_new_answer").append_new_line()
        return jsonify(ret), HTTP_500_INTERNAL_SERVER_ERROR
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@answers.put("/sets/<string:set_id>/questions/<string:question_id>/answers/<string:answer_id>")
@swag_from("../docs/answers/update.yaml")
@user_token_required
def delete_set(user_id, set_id, question_id, answer_id):
    try:
        # Create connection
        conn = get_db_connection()
        cursor = conn.cursor() 

        # Check if set_id and question_id is uuid type or not
        if not is_valid_uuid(set_id) or not is_valid_uuid(question_id) or not is_valid_uuid(answer_id):
            ret = {
                    'status': False,
                    'message':'Type of set_id and question_id and answer_id must is uuid!'
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
        
        # Check if question don't include answer
        query4 = sql.SQL('''select * from public.answer where question_id = %s and id = %s''')
        cursor.execute(query4, (question_id, answer_id, ))

        check_question_answer = cursor.fetchone()
        if check_question_answer is None or len(check_question_answer) == 0:
            ret = {
                'status': False,
                'message': 'Sorry, question do not include answer!'
            }
            return jsonify(ret), HTTP_400_BAD_REQUEST
        
        # Return response
        ret = {
                'status': True,
                'message':'Delete question successfully!'
            }
        
        # Get now content and is_correct
        query5 = sql.SQL('''select content, is_correct from public.answer where id = %s''')
        cursor.execute(query5, (answer_id, ))
        content_is_correct = cursor.fetchone()

        # Now content, is_correct 
        now_content = content_is_correct[0]
        now_is_correct = content_is_correct[1]

        # Get content from request
        content = ""
        if 'content' in request.json:
            content = request.json['content']

        # Get is_correct from request
        is_correct = ""
        if 'is_correct' in request.json:
            is_correct = request.json['is_correct']
        
        # Update answer information
        if content == "" and is_correct == "":
            ret['data'] = {
                'id': answer_id,
                'content': now_content,
                'is_correct': now_is_correct
            }

        query4 = sql.SQL('''update public.answer set content = %s, is_correct = %s where id = %s''')
        
        cursor.execute(query4, (now_content if content == "" else content, now_is_correct if is_correct == "" else is_correct, answer_id))
        conn.commit()

        ret['data'] = {
                'id': answer_id,
                'content': now_content if content == "" else content,
                'is_correct': now_is_correct if is_correct == "" else is_correct
            }
        
        return jsonify(ret), HTTP_204_NO_CONTENT
    except Exception as e:
        ret = {
            'status': False,
            'message': str(e)
        }
        Systemp_log(traceback.format_exc(), "update_answer").append_new_line()
        return jsonify(ret), HTTP_500_INTERNAL_SERVER_ERROR
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@answers.delete("/sets/<string:set_id>/questions/<string:question_id>/answers/<string:answer_id>")
@swag_from("../docs/answers/delete.yaml")
@user_token_required
def delete_set(user_id, set_id, question_id, answer_id):
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

        # Check if question don't include answer
        query4 = sql.SQL('''select * from public.answer where question_id = %s and id = %s''')
        cursor.execute(query4, (question_id, answer_id, ))

        check_question_answer = cursor.fetchone()
        if check_question_answer is None or len(check_question_answer) == 0:
            ret = {
                'status': False,
                'message': 'Sorry, question do not include answer!'
            }
            return jsonify(ret), HTTP_400_BAD_REQUEST
        
        # Update question information
        query5 = sql.SQL('''update public.answer set is_deleted = %s where id = %s''')
        
        cursor.execute(query5, (True, answer_id, ))
        conn.commit()

        # Return response
        ret = {
                'status': True,
                'message':'Delete answer successfully!'
            }
        
        return jsonify(ret), HTTP_204_NO_CONTENT
    except Exception as e:
        ret = {
            'status': False,
            'message': str(e)
        }
        Systemp_log(traceback.format_exc(), "delete_answer").append_new_line()
        return jsonify(ret), HTTP_500_INTERNAL_SERVER_ERROR
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()