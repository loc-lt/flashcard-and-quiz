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
import random
from utils.validators import validate_email, validate_name, validate_integer, is_boolean, is_valid_uuid
from utils.database import get_db_connection 

tests = Blueprint("tests", __name__, url_prefix="/api/v1/tests")

# Finalize a test: with COMPLETED mode or save_draft a test: with IN_PROGRESS mode
@tests.post("")
@swag_from("../docs/testes/create.yaml")
@user_token_required
@quiz_id_required
def create_test(user_id, quiz_id):
    try:
        # Create connection
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get mode (IN_PROGRESS or COMPLETED)
        mode = request.json['mode']

        if mode not in ['COMPLETED', 'IN_PROGRESS']:
            ret = {
                'status': False,
                'message': 'Mode is not exist!'
            }
            return jsonify(ret), HTTP_400_BAD_REQUEST

        # Get all information of all answers of tests
        '''
        {
            'quiz_id': 'xxxxx'
            'mode': 'xxxxx',
            'questions': [
                {
                    'id': 'xxxxx', # foreign key to quiz_question table ~ question_id
                    'type': 'xxxxx',
                    'solutions':
                        {
                            'text_answer': 'xxxxx',
                            'multiple_choice_answer': 'xxxxx' # foreign key to quiz_question_answer table ~ answer_id
                            'checkboxes_answer': ['xxxxx', 'yyyyy'] # list foreign key of quiz_question_answer table ~ answer_ids
                        }
                }
            ]
        }
        '''

        # Insert into test table to get test_id
        cursor.execute('''insert into public.test (user_id, quiz_id, created_at, updated_at, is_deleted, mode)
                       values (%s, %s, %s, %s, %s, %s) returning id;''',
                       (user_id, quiz_id,datetime.datetime.now(), datetime.datetime.now(), False, mode))
        test_id = cursor.fetchone()[0]

        # Get all question
        questions = request.json['questions']
        
        sum_true_questions = 0

        for question_solution in questions:
            quiz_question_id = question_solution['id']
            question_type = question_solution['type']
            solutions = question_solution['solutions']

            # Get all solution of a question
            text_answer = solutions['text_answer']
            multiple_choice_answer = solutions['multiple_choice_answer']
            checkboxes_answer = solutions['checkboxes_answer']

            # Check true question
            if is_correct_answer(quiz_question_id, solutions):
                sum_true_questions += 1

            # Save to solution table
            cursor.execute('''insert into public.solution (test_id, quiz_question_id, text_answer, multiple_choice_answer, checkboxes_answer, created_at, updated_at, is_deleted)
                           values (%s, %s, %s, %s, %s, %s, %s, %s)''', 
                           (test_id, quiz_question_id, text_answer, multiple_choice_answer, checkboxes_answer, datetime.datetime.now(), datetime.datetime.now(), False))

        # If mode is COMPLETED: calculate score base on sum of true questions / sum all question of test
        if mode == 'COMPLETED':
            score = round(sum_true_questions/len(questions), 2)

            # Update score for test
            cursor.execute('''update public.test set score = %s where id = %s''', (score, test_id, ))
        
        # Commit
        cursor.commit()

        if mode == 'COMPLETED':
            ret = {
                'status': True,
                'message': 'Finalize test successfully!',
                'id': test_id
            }
            return jsonify(ret), HTTP_201_CREATED
        elif mode == 'IN_PROGRESS':
            ret = {
                'status': True,
                'message': 'Save draft test successfully!',
                'id': test_id
            }
            return jsonify(ret), HTTP_201_CREATED
        
    except Exception as e:
        ret = {
            'status': False,
            'message': str(e)
        }
        Systemp_log(traceback.format_exc(), "create_new_test").append_new_line()
        return jsonify(ret), HTTP_500_INTERNAL_SERVER_ERROR
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Get a test (with both IN_PROGRESS and COMPLETED mode) 
@tests.get("/<string:test_id>")
@swag_from('../docs/testes/get.yaml')
@user_token_required
def get_test(user_id, test_id):
    try:
        # Create connection
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if test_id is uuid type or not
        if not is_valid_uuid(test_id):
            ret = {
                    'status': False,
                    'message':'Type of test_id must is uuid!'
                }
            return jsonify(ret), HTTP_400_BAD_REQUEST  
        
        # Check if user is deleted
        cursor.execute('''select is_deleted from public."user" where id = %s''', (user_id, ))
        is_deleted = cursor.fetchone()

        if not is_deleted:
            ret = {
                    'status': False,
                    'message':'Owner of test has been deleted!'
                }
            return jsonify(ret), HTTP_400_BAD_REQUEST
        
        # Check if test is not exist or is deleted 
        cursor.execute('''select is_deleted from public.test where id = %s''', (test_id, ))

        check_deleted = cursor.fetchone()

        if check_deleted is None:
            ret = {
                'status':False,
                'message':'This test is not exist!'
            }
            return jsonify(ret), HTTP_400_BAD_REQUEST
        
        if check_deleted[0]: 
            ret = {
                'status':False,
                'message':'This test has been deleted!'
            }
            return jsonify(ret), HTTP_400_BAD_REQUEST
        
        # Check if user isn't owner of test
        cursor.execute('''select * from public.test where user_id = %s and id = %s''', (user_id, test_id, ))
        check_test_user = cursor.fetchone()
        
        if check_test_user is None or len(check_test_user) == 0:
            ret = {
                    'status': False,
                    'message':'Sorry, permission denied!'
                }
            return jsonify(ret), HTTP_400_BAD_REQUEST
        
        # Get all question_id of test
        cursor.execute('''select a.id, c.question_content, d.content, d.is_correct  
                       from public.test a
                       join public.quiz b
                       on a.quiz_id = b.id and a.id = %s
                       join public.quiz_question c
                       on b.id = c.quiz_id
                       join public.quiz_question_answer d
                       on c.id = d.quiz_question_id''',
                       (test_id, ))
        
        question_test = cursor.fetchall()

        # Return response
        ret = {
                'status': True,
                'message':'Get solution of test successfully!',
                'data': []
            }

        if len(question_test) == 0:
            ret['data'] = None
            return jsonify(ret), HTTP_200_OK
        
        # Get all questions ans its answers of quiz
        question_content = ''
        answers_information = []

        for idx, item in enumerate(question_test):
            if question_content == '':
                question_content = item[1]
                answers_information.append({
                    'answer_content': item[2],
                    'is_correct': item[3]
                })
            elif item[1] != question_content:
                # Add solution of question before add to ret['data]
                ret['data'].append({
                    'question_content': question_content,
                    'answers': answers_information
                })
                answers_information = [{'question_content': item[2], 'is_correct': item[3]}]
                question_content = item[1]
            else:
                answers_information.append({
                    'answer_content': item[2],
                    'is_correct': item[3]
                })

            if idx == len(question_test) -1:
                # Add solution of question before add to ret['data]
                ret['data'].append({
                    'question_content': question_content,
                    'answers': answers_information
                })

    except:
        pass