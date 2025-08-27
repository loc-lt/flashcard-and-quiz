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

quizzes = Blueprint("quizzes", __name__, url_prefix="/api/v1/quizzes")

@quizzes.post("")
@swag_from("../docs/quizzes/create.yaml")
@user_token_required
@set_id_required
def create_quiz(user_id, set_id):
    try:
        # Create connection
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get number of questions and question types of quiz
        quantities = request.json['quantities']
        types = request.json['types']
        
        # Initialize list all_questions
        all_questions = []
        
        # Get list question
        for type, quantity in zip(types, quantities):
            query1 = sql.SQL('''select * from public.question where set_id = %s and type = %s order by random() limit %s;''')
            cursor.execute(query1, (set_id, type, quantity, ))
            quiz_questions = cursor.fetchall()

            for item in quiz_questions:

                # Get list answer from question_id
                cursor.execute("select * from public.answer where question_id = %s")
                answers_question = cursor.fetchall()
                
                # Initialize list all_answers
                all_answers = []

                for item in answers_question:
                    all_answers.append({
                        'id': item[0],
                        'content': item[1],
                        'is_correct': item[2]
                    })

                all_questions.append({
                    'id': item[0],
                    'content': item[1],
                    'type': item[2],
                    'set_id': item[3],
                    'answers': all_answers
                })

        # Shuffle the list
        random.shuffle(all_questions)
        
        # Start transaction
        cursor.execute('BEGIN')

        # Insert into quiz table
        query2 = sql.SQL('''insert into public.quiz (created_at, updated_at, is_deleted, user_id, set_id, public_or_not)
                       values (%s, %s, %s, %s, %s, %s) returning id;''')
        cursor.execute(query2, (datetime.datetime.now(), datetime.datetime.now(), False, user_id, set_id, False))
        id_return = cursor.fetchone()

        # Insert into quiz_question and quiz_question_answer table
        query3 = sql.SQL('''insert into public.quiz_question(quiz_id, question_id, question_content, created_at, updated_at, is_deleted) 
                         values (%s, %s, %s, %s, %s, %s) returning id;''')
        
        query4 = sql.SQL('''insert into public.quiz_question_answer(quiz_question_id, content, is_correct, created_at, updated_at, is_deleted)
                         values (%s, %s, %s, %s, %s, %s)''')
        
        for item in all_questions:
            cursor.execute(query3, (id_return[0], item['id'], item['content'], datetime.datetime.now(), datetime.datetime.now(), False))
            quiz_question_id = cursor.fetchone()

            for answer_item in item['answers']:
                cursor.execute(query4, (quiz_question_id[0], answer_item['content'], answer_item['is_correct'], datetime.datetime.now(), datetime.datetime.now(), False))

        # Commit transaction
        conn.commit()

        ret = {
                'status': True,
                'message':'Create new quiz successfully!',
                'id': id_return[0]
            }
        
        return jsonify(ret), HTTP_200_OK
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

# Submit a quiz (only owner or shared users can access to quiz, can leave some questions unanswered, if any answer is bad request, don't save quiz result)

# Get all questions and its answers of a quiz (currently, not created in the past -> to get the most updated questions)
@quizzes.get("/current/<string:quiz_id>")
@swag_from("../docs/quizzes/all_questions.yaml")
@user_token_required
@set_id_required
def get_all_questions_of_quiz(user_id, quiz_id):
    try:
        # Create connection
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if quiz_id is uuid type or not
        if not is_valid_uuid(quiz_id):
            ret = {
                'status': False,
                'message': 'Type of quiz_id must is uuid!'
            }
            return jsonify(ret), HTTP_400_BAD_REQUEST
        
        # Check if quiz is not exist or is deleted
        query = sql.SQL('''select is_deleted from public.quiz where id = %s''')
        cursor.execute(query, (quiz_id, ))
        check_deleted = cursor.fetchone()

        if check_deleted is None:
            ret = {
                'status': False,
                'message': 'This quiz is not exist!'
            }
            return jsonify(ret), HTTP_400_BAD_REQUEST
        
        if check_deleted:
            ret = {
                'status': False,
                'message': 'This quiz has been deleted!'
            }
            return jsonify(ret), HTTP_400_BAD_REQUEST

        # Check if user is't owner of quiz (no need to check set which quiz is created is deleted or not)
        query1 = sql.SQL('''select * from public.quiz where id = %s and user_id = %s''')
        cursor.execute(query1, (quiz_id, user_id, ))
        
        check_owner = cursor.fetchone()
        if check_owner is not None and len(check_owner) == 0:
            ret = {
                'status': False,
                'message': 'Sorry, permissions denied!'
            }
        
        # Get all questions of quiz
        query2 = sql.SQL('''select a.id, b.content, c.content, c.is_correct
                         from public.quiz a
                         join public.quiz_question b
                         on a.id = b.quiz_id and a.id = %s
                         join public.question c
                         on b.question_id = c.id
                         join public.answer d
                         on c.id = d.question_id''')
        
        cursor.execute(query2, (quiz_id, ))
        questions_quiz = cursor.fetchall()

        if questions_quiz is None:
            ret = {
                'status': False,
                'message': 'Get all questions and answers failed!'
            }
            return jsonify(ret), HTTP_500_INTERNAL_SERVER_ERROR
        
        # Return response
        ret = {
                'status': True,
                'message':'Get all questions successfully!',
                'data': []
            }

        if len(questions_quiz) == 0:
            ret['data'] = None
            return jsonify(ret), HTTP_200_OK
        
        # Get all questions ans its answers of quiz
        question_content = ''
        answers_information = []

        for idx, item in enumerate(questions_quiz):
            if question_content == '':
                question_content = item[1]
                answers_information.append({
                    'answer_content': item[2],
                    'is_correct': item[3]
                })
            elif item[1] != question_content:
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

            if idx == len(questions_quiz) -1:
                ret['data'].append({
                    'question_content': question_content,
                    'answers': answers_information
                })

        return jsonify(ret), HTTP_200_OK
    except Exception as e:
        ret = {
            'status': False,
            'message': str(e)
        }
        Systemp_log(traceback.format_exc(), "get_all_questions_of_quiz").append_new_line()
        return jsonify(ret), HTTP_500_INTERNAL_SERVER_ERROR
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Get all quiz results (currently, not created in the past -> to get the most updated questions)
@quizzes.get("/current")
@swag_from("../docs/quizzes/all_quizzes_questions.yaml")
@user_token_required
def get_all_questions_of_all_quizzes(user_id):
    try:
        # Create connection
        conn = get_db_connection()
        cursor = conn.cursor()

        # Query to get all quiz_ids
        query1 = sql.SQL('''select distinct(id) from public.quiz where user_id = %s''')
        cursor.execute(query1, (user_id, ))
        all_ids = cursor.fetchall()
        
        quiz_ids = [id[0] for id in all_ids]

        # Initialize ret if get question_quizzes from database successfully
        ret = {
            'status': True,
            'message': 'Get all quizzes and questions and answers successfully!',
            'data': []
        }

        for quiz_id in quiz_ids:
            # Get all questions and answers
            query2 = sql.SQL('''select a.quiz_id, b.content, c.content, c.is_correct
                            from public.quiz a
                            join public.quiz_question b
                            on a.id = b.quiz_id and a.id = %s
                            join public.question c
                            on b.question_id = c.id
                            join public.answer d
                            on c.id = d.question_id''')
            
            cursor.execute(query2, (quiz_id, ))
            questions_answers = cursor.fetchall()

            if questions_answers is None or len(questions_answers) == 0:
                continue

            quiz_dict = {}

            # Get quiz id
            quiz_dict['id'] = questions_answers[0]

            # Initialize list of questions
            quiz_dict['questions'] = []

            # Get all questions ans its answers of quiz
            question_content = ''
            answers_information = []

            for idx, item in enumerate(questions_answers):
                if question_content == '':
                    question_content = item[1]
                    answers_information.append({
                        'answer_content': item[2],
                        'is_correct': item[3]
                    })
                elif item[1] != question_content:
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

                if idx == len(questions_answers) -1:
                    ret['data'].append({
                        'question_content': question_content,
                        'answers': answers_information
                    })

            ret['data'].append(quiz_dict)

        return jsonify(ret), HTTP_200_OK
    except Exception as e:
        ret = {
            'status': False,
            'message': str(e)
        }
        Systemp_log(traceback.format_exc(), "get_all_questions_of_all_quizzes").append_new_line()
        return jsonify(ret), HTTP_500_INTERNAL_SERVER_ERROR
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Get all questions and its answers of a quiz (created in the past)
@quizzes.get("/<string:quiz_id>")
@swag_from("../docs/quizzes/all_questions_when_created.yaml")
@user_token_required
@set_id_required
def get_all_questions_of_quiz_when_created(user_id, quiz_id):
    try:
        # Create connection
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if quiz_id is uuid type or not
        if not is_valid_uuid(quiz_id):
            ret = {
                'status': False,
                'message': 'Type of quiz_id must is uuid!'
            }
            return jsonify(ret), HTTP_400_BAD_REQUEST
        
        # Check if quiz is not exist or is deleted
        query = sql.SQL('''select is_deleted from public.quiz where id = %s''')
        cursor.execute(query, (quiz_id, ))
        check_deleted = cursor.fetchone()

        if check_deleted is None:
            ret = {
                'status': False,
                'message': 'This quiz is not exist!'
            }
            return jsonify(ret), HTTP_400_BAD_REQUEST
        
        if check_deleted:
            ret = {
                'status': False,
                'message': 'This quiz has been deleted!'
            }
            return jsonify(ret), HTTP_400_BAD_REQUEST

        # Check if user is't owner of quiz (no need to check set which quiz is created is deleted or not)
        query1 = sql.SQL('''select * from public.quiz where id = %s and user_id = %s''')
        cursor.execute(query1, (quiz_id, user_id, ))
        
        check_owner = cursor.fetchone()
        if check_owner is not None and len(check_owner) == 0:
            ret = {
                'status': False,
                'message': 'Sorry, permissions denied!'
            }
        
        # Get all questions of quiz
        query2 = sql.SQL('''select a.quiz_id, b.content, c.content, c.is_correct
                         from public.quiz a
                         join public.quiz_question b
                         on a.id = b.quiz_id and a.id = %s
                         join public.quiz_question_answer c
                         on b.id = c.quiz_question_id''')
        
        cursor.execute(query2, (quiz_id, ))
        questions_quiz = cursor.fetchall()

        if questions_quiz is None:
            ret = {
                'status': False,
                'message': 'Get all questions and answers failed!'
            }
            return jsonify(ret), HTTP_500_INTERNAL_SERVER_ERROR
        
        # Return response
        ret = {
                'status': True,
                'message':'Get all questions successfully!',
                'data': []
            }

        if len(questions_quiz) == 0:
            ret['data'] = None
            return jsonify(ret), HTTP_200_OK
        
        # Get all questions ans its answers of quiz
        question_content = ''
        answers_information = []

        for idx, item in enumerate(questions_quiz):
            if question_content == '':
                question_content = item[1]
                answers_information.append({
                    'answer_content': item[2],
                    'is_correct': item[3]
                })
            elif item[1] != question_content:
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

            if idx == len(questions_quiz) -1:
                ret['data'].append({
                    'question_content': question_content,
                    'answers': answers_information
                })

        return jsonify(ret), HTTP_200_OK
    except Exception as e:
        ret = {
            'status': False,
            'message': str(e)
        }
        Systemp_log(traceback.format_exc(), "get_all_questions_of_quiz").append_new_line()
        return jsonify(ret), HTTP_500_INTERNAL_SERVER_ERROR
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Get all quiz results (created in the past)
@quizzes.get("")
@swag_from("../docs/quizzes/all_quizzes_questions_when_created.yaml")
@user_token_required
def get_all_questions_of_all_quizzes_when_created(user_id):
    try:
        # Create connection
        conn = get_db_connection()
        cursor = conn.cursor()

        # Query to get all quiz_ids
        query1 = sql.SQL('''select distinct(id) from public.quiz where user_id = %s''')
        cursor.execute(query1, (user_id, ))
        all_ids = cursor.fetchall()
        
        quiz_ids = [id[0] for id in all_ids]

        # Initialize ret if get question_quizzes from database successfully
        ret = {
            'status': True,
            'message': 'Get all quizzes and questions and answers successfully!',
            'data': []
        }

        for quiz_id in quiz_ids:
            # Get all questions and answers
            query2 = sql.SQL('''select a.quiz_id, b.content, c.content, c.is_correct
                         from public.quiz a
                         join public.quiz_question b
                         on a.id = b.quiz_id and a.id = %s
                         join public.quiz_question_answer c
                         on b.id = c.quiz_question_id''')
            
            cursor.execute(query2, (quiz_id, ))
            questions_answers = cursor.fetchall()

            if questions_answers is None or len(questions_answers) == 0:
                continue

            quiz_dict = {}

            # Get quiz id
            quiz_dict['id'] = questions_answers[0]

            # Initialize list of questions
            quiz_dict['questions'] = []

            # Get all questions ans its answers of quiz
            question_content = ''
            answers_information = []

            for idx, item in enumerate(questions_answers):
                if question_content == '':
                    question_content = item[1]
                    answers_information.append({
                        'answer_content': item[2],
                        'is_correct': item[3]
                    })
                elif item[1] != question_content:
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

                if idx == len(questions_answers) -1:
                    ret['data'].append({
                        'question_content': question_content,
                        'answers': answers_information
                    })

            ret['data'].append(quiz_dict)

        return jsonify(ret), HTTP_200_OK
    except Exception as e:
        ret = {
            'status': False,
            'message': str(e)
        }
        Systemp_log(traceback.format_exc(), "get_all_questions_of_all_quizzes").append_new_line()
        return jsonify(ret), HTTP_500_INTERNAL_SERVER_ERROR
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Share a quiz with other users or public