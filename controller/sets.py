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

        # Get name from request (required)
        if 'name' not in request.json:
            ret = {
                    'status': False,
                    'message':'Please fill out name field!'
                }
            return jsonify(ret), HTTP_400_BAD_REQUEST  
        name = request.json['name']

        # Get description from request (optional)
        description = None
        if 'description' in request.json:
            description = request.json['description']
        
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

        # Save new set
        query2 = sql.SQL('''insert into public.set (user_id, created_at, updated_at, is_deleted, public_or_not, name, description) 
                        values (%s, %s, %s, %s, %s, %s, %s) returning id;''')
        cursor.execute(query2, (user_id, datetime.datetime.now(), datetime.datetime.now(), False, False, name, description))
        return_id = cursor.fetchone()
        conn.commit()

        # Return response
        ret = {
                'status': True,
                'message':'Create new set successfully!',
                'id': return_id[0]
            }
        
        return jsonify(ret), HTTP_201_CREATED
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

@sets.put("/<string:set_id>")
@swag_from("../docs/sets/update.yaml")
@user_token_required
def update_set(user_id, set_id = None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get name from request
        name = None
        if name in request.json:
            name = request.json['name']
        
        # Get description from request
        description = None
        if description in request.json:
            description = request.json['description']

        # Check if set_id is filled in or not
        if set_id is None:
            ret = {
                    'status': False,
                    'message':'Set ID is required!'
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
        
        user_deleted = cursor.fetchone()
        if not user_deleted[0]:
            ret = {
                    'status': False,
                    'message':'Set owner has been deleted!'
                }
            return jsonify(ret), HTTP_400_BAD_REQUEST
        
        # Check if set is deleted
        query2 = sql.SQL('''select is_deleted from public.set where id = %s''')
        cursor.execute(query2, (set_id, ))

        set_deleted = cursor.fetchone()
        if not set_deleted[0]:
            ret = {
                'status': False,
                'message': 'This set has been deleted!'
            }
            return jsonify(ret), HTTP_400_BAD_REQUEST

        # Check if user isn't owner of this set
        query3 = sql.SQL('''select * from public.set where user_id = %s and id = %s''')
        cursor.execute(query3, (user_id, set_id))

        check_owner = cursor.fetchone()
        if check_owner is not None and len(check_owner) == 0:
            ret = {
                    'status': False,
                    'message':'Sorry, permission denied!'
                }
            return jsonify(ret), HTTP_403_FORBIDDEN
        
        # Update set information
        query4 = sql.SQL('''update public.set set name = %s, description = %s, updated_at = %s where id = %s returning id, name, description;''')
        cursor.execute(query4, (name, description, datetime.datetime.now(), set_id))
        updated_infors = cursor.fetchone()
        conn.commit()

        # Return response
        ret = {
                'status': True,
                'message':'Update set successfully!',
                'updated_set': {
                    'id': updated_infors[0],
                    'name': updated_infors[1],
                    'description': updated_infors[2]
                }
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
def delete_set(user_id, set_id = None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if set_id is filled in or not
        if set_id is None:
            ret = {
                    'status': False,
                    'message':'Set ID is required!'
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
        
        # Update set information
        query3 = sql.SQL('''update public.set set is_deleted = %s where id = %s''')
        cursor.execute(query3, (True, set_id))
        conn.commit()

        # Return response
        ret = {
                'status': True,
                'message':'Delete set successfully!'
            }
        
        return jsonify(ret), HTTP_204_NO_CONTENT
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

# READ ONE
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
        
        # Get all questions and answers
        query3 = sql.SQL('''select a.name, a.description, b.content, c.content, c.is_correct  
                        from public.set a 
                        join public.question b 
                        on a.id = b.set_id and b.set_id = %s and b.is_deleted != true
                        join public.answer c
                        on b.id = c.question_id and c.is_deleted != true
                        ''')
        
        cursor.execute(query3, (set_id, ))
        questions_answers = cursor.fetchall()

        if questions_answers is None:
            ret = {
                    'status': False,
                    'message':'Get all questions and answers failed!'
                }
            return jsonify(ret), HTTP_500_INTERNAL_SERVER_ERROR
        
        # Initialize ret if get questions_answers from database successfully
        ret = {
                'status': True,
                'message':'Get all questions and answers successfully!',
                'data': {}
            }
        
        if len(questions_answers) == 0:
            return jsonify(ret), HTTP_200_OK

        # Get set name 
        ret['data']['name'] = questions_answers[0][0]

        # Get set description
        ret['data']['description'] = questions_answers[0][1]

        # Initialize list of question
        ret['data']['questions'] = []

        # Get all questions and answers
        question_content = ''
        answers_infors = []

        for idx, item in enumerate(questions_answers):
            if question_content == '':
                question_content = item[2]
                answers_infors.append({'answer_content': item[3], 'is_correct': item[4]})
            elif item[2] != question_content:
                ret['data']['questions'].append({'question_content': question_content, 'answers': answers_infors})
                answers_infors = [{'question_content': item[3], 'is_correct': item[4]}]
                question_content = item[2]
            else:
                answers_infors.append({'answer_content': item[3], 'is_correct': item[4]})

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

# READ ALL (get all sets with questions with answer which is owned by user send request)
@sets.get("")
@swag_from("../docs/sets/all_sets_questions.yaml")
@user_token_required
def get_all_questions_of_all_sets(user_id):
    try:
        # Create connection
        conn = get_db_connection()
        cursor = conn.cursor()  

        # Query to get all set_ids
        query1 = sql.SQL('''select distinct(id) from public."set" where user_id = %s and is_deleted != true''')
        cursor.execute(query1, (user_id, ))
        all_ids = cursor.fetchall()

        set_ids = [id[0] for id in all_ids]

        # Initialize ret if get questions_answers from database successfully
        ret = {
                'status': True,
                'message':'Get all sets and questions and answers successfully!',
                'data': []
            }
        
        for set_id in set_ids:
            # Get all questions and answers
            query2 = sql.SQL('''select a.name, a.description, b.content, c.content, c.is_correct  
                        from public.set a 
                        join public.question b 
                        on a.id = b.set_id and b.set_id = %s and b.is_deleted != true
                        join public.answer c
                        on b.id = c.question_id and c.is_deleted != true
                        ''')
        
            cursor.execute(query2, (set_id, ))
            questions_answers = cursor.fetchall()

            if questions_answers is None or len(questions_answers) == 0:
                continue

            set_dict = {}

            # Get set name 
            set_dict['name'] = questions_answers[0][0]

            # Get set description
            set_dict['description'] = questions_answers[0][1]

            # Initialize list of question
            set_dict['questions'] = []

            # Get all questions and answers
            question_content = ''
            answers_infors = []

            for idx, item in enumerate(questions_answers):
                if question_content == '':
                    question_content = item[2]
                    answers_infors.append({'answer_content': item[3], 'is_correct': item[4]})
                elif item[2] != question_content:
                    set_dict['questions'].append({'question_content': question_content, 'answers': answers_infors})
                    answers_infors = [{'question_content': item[3], 'is_correct': item[4]}]
                    question_content = item[2]
                else:
                    answers_infors.append({'answer_content': item[3], 'is_correct': item[4]})

                if idx == len(questions_answers) - 1:
                    set_dict['questions'].append({'question_content': question_content, 'answers': answers_infors})

            ret['data'].append(set_dict)

        return jsonify(ret), HTTP_200_OK
    except Exception as e:
        ret = {
            'status': False,
            'message': str(e)
        }
        Systemp_log(traceback.format_exc(), "get_all_questions_of_all_sets").append_new_line()
        return jsonify(ret), HTTP_500_INTERNAL_SERVER_ERROR
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# SEARCH
@sets.post("/search")
@swag_from("../docs/sets/search.yaml")
@user_token_required
@set_id_required
def search(user_id, set_id):
    try:
        # Create connection
        conn = get_db_connection()
        cursor = conn.cursor()  

        # Check if set_id is uuid type or not
        if not is_valid_uuid(set_id):
            ret = {
                'status': False,
                'message': 'Type of set_id must be uuid!'
            }
            return jsonify(ret), HTTP_400_BAD_REQUEST  
        
        # Check if set is not exist or is deleted 
        query1 = sql.SQL('''SELECT is_deleted FROM public.set WHERE id = %s''')
        cursor.execute(query1, (set_id, ))

        check_deleted = cursor.fetchone()

        if check_deleted is None:
            ret = {
                'status': False,
                'message': 'This set does not exist!'
            }
            return jsonify(ret), HTTP_400_BAD_REQUEST
        
        if check_deleted[0]: 
            ret = {
                'status': False,
                'message': 'This set has been deleted!'
            }
            return jsonify(ret), HTTP_400_BAD_REQUEST
        
        # Check if user isn't owner of this set
        query2 = sql.SQL('''SELECT * FROM public.set WHERE user_id = %s AND id = %s''')
        cursor.execute(query2, (user_id, set_id))

        check_owner = cursor.fetchone()
        if check_owner is None:
            ret = {
                'status': False,
                'message': 'Sorry, permission denied!'
            }
            return jsonify(ret), HTTP_403_FORBIDDEN
        
        # Pagination and Filtering
        page = request.json['page']
        page_size = request.json['page_size']
        keyword = request.json['keyword']
        question_type = request.json['question_type']
        sort_by = request.json['sort_by']
        sort_direction = request.json['sort_direction']

        offset = (page - 1) * page_size # example: page = 2, page_size = 50 -> offset = (2 - 1)*50 = 50 -> get records from 51 -> 100
        
        # Chú ý: số lượng phần tử có chứa %s (format string) phải bằng độ dài list query_params,
        # sau này sẽ dùng từng phần tử trong query_params để map tới từng format string để add vào query tổng
        query_params = [set_id]
        filters = ["b.set_id = %s", "b.is_deleted != true", "c.is_deleted != true"]

        # Kiểm tra xem điều kiện search có keyword không, nếu có thì thêm vào cả filters và query_params
        if keyword:
            filters.append("(b.content ILIKE %s OR c.content ILIKE %s)")
            query_params.append(f"%{keyword}%") # map vào %s đầu tiên trong (b.content ILIKE %s OR c.content ILIKE %s)
            query_params.append(f"%{keyword}%") # map vào %s thứ hai trong (b.content ILIKE %s OR c.content ILIKE %s)
        
        # Kiểm tra xem điều kiện search có question không, nếu có thì thêm vào cả filters và query_params
        if question_type:
            filters.append("b.type = %s")
            query_params.append(question_type)
        
        sort_column = sql.Identifier(sort_by)
        sort_order = sql.SQL('ASC') if sort_direction == 'asc' else sql.SQL('DESC')

        query3 = sql.SQL('''SELECT a.description, b.content AS question_content, c.content AS answer_content, c.is_correct  
                            FROM public.set a 
                            JOIN public.question b ON a.id = b.set_id
                            JOIN public.answer c ON b.id = c.question_id
                            WHERE {} 
                            ORDER BY {} {}
                            LIMIT %s OFFSET %s''').format(
            sql.SQL(' AND ').join(map(sql.SQL, filters)),
            sort_column,
            sort_order
        )

        query_params.extend([page_size, offset])

        cursor.execute(query3, query_params)
        questions_answers = cursor.fetchall()

        ret = {
            'status': True,
            'message': 'Get all questions and answers successfully!',
            'data': {}
        }

        if questions_answers:
            # Get set's description
            ret['data']['description'] = questions_answers[0][0]

            # Initialize list of question
            ret['data']['questions'] = []

            # Get all questions and answers
            question_content = ''
            answers_infors = []

            for idx, item in enumerate(questions_answers):
                if question_content == '':
                    question_content = item[1]
                    answers_infors.append({'answer_content': item[2], 'is_correct': item[3]})
                elif item[1] != question_content:
                    ret['data']['questions'].append({'question_content': question_content, 'answers': answers_infors})
                    answers_infors = [{'answer_content': item[2], 'is_correct': item[3]}]
                    question_content = item[1]
                else:
                    answers_infors.append({'answer_content': item[2], 'is_correct': item[3]})

                if idx == len(questions_answers) - 1:
                    ret['data']['questions'].append({'question_content': question_content, 'answers': answers_infors})
        else:
            ret['data']['description'] = ''
            ret['data']['questions'] = []

        return jsonify(ret), HTTP_200_OK
    except Exception as e:
        ret = {
            'status': False,
            'message': str(e)
        }
        traceback.print_exc()  # Log lỗi ra console để debug
        return jsonify(ret), HTTP_500_INTERNAL_SERVER_ERROR
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()