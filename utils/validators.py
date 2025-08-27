import re
import validators
import uuid
from constants.http_status_code import *
from utils.database import *

def validate_email(email):
    """Kiểm tra tính hợp lệ của địa chỉ email."""
    return validators.email(email)

def validate_name(name):
    """Kiểm tra xem tên có chứa ký tự đặc biệt hay không."""
    # Ký tự đặc biệt được xác định là bất kỳ ký tự nào không phải chữ cái hoặc số.
    special_characters = re.compile('[@_!#$%^&*()<>?/\\|}{~:]')
    if special_characters.search(name) is not None:
        return False
    return True

def validate_integer(value):
    """Kiểm tra xem giá trị có phải là số nguyên hay không."""
    if isinstance(value, int):
        return True
    if isinstance(value, str) and value.isdigit():
        return True
    return False

def is_boolean(value):
    return isinstance(value, bool)

def is_valid_uuid(uuid_str):
    try:
        # Kiểm tra xem uuid_str có hợp lệ không
        uuid_obj = uuid.UUID(uuid_str, version=4)
        return True
    except ValueError:
        return False
    
def is_valid_question_type(type):
    return type in ['Text_Fill', 'Multiple_Choice', 'Checkboxes']

def count_correct_answers(list_answers):
    count = 0
    for answer in list_answers:
        if answer['is_correct'] in [True, "True"] :
            count += 1
    return count

def validate_question_and_answers(question_type, list_answers):
    print(len(list_answers))
    print(count_correct_answers(list_answers))
    if question_type == 'Text_Fill':
        if len(list_answers) != 1:
            return 'Text fill question has only one answer!', HTTP_400_BAD_REQUEST
        elif count_correct_answers(list_answers) != 1:
            return 'Answer of text fill question must be correct!', HTTP_400_BAD_REQUEST
    elif question_type == 'Multiple_Choice':
        if len(list_answers) < 2:
            return 'Multiple choice question must have more than one answer!', HTTP_400_BAD_REQUEST
        elif count_correct_answers(list_answers) != 1:
            return 'Multiple choice question must have only one correct answer!', HTTP_400_BAD_REQUEST
    elif question_type == 'Checkboxes':
        if len(list_answers) == count_correct_answers(list_answers):
            return "Amount of correct answers must less than amount of answers!", HTTP_400_BAD_REQUEST
        if len(list_answers) < 3:
            return 'Checkboxes question must have more than two answers!', HTTP_400_BAD_REQUEST
        elif count_correct_answers(list_answers) < 2:
            return 'Checkboxes question must have more than one correct answer!', HTTP_400_BAD_REQUEST
    return None

def is_correct_answer(quiz_question_id, solutions):
    try:
        # Create connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all answer of question
        cursor.execute('''select answer_id, content 
                    from public.quiz_question_answer 
                    where quiz_question_id = %s''',
                        (quiz_question_id, ))
        
        all_answers = cursor.fetchall()
        
        # Get all true answer of question
        cursor.execute('''select answer_id, content 
                    from public.quiz_question_answer 
                    where quiz_question_id = %s and is_correct = %s''',
                        (quiz_question_id, True, ))
        
        true_answers = cursor.fetchall()

        if len(all_answers) == 1 and len(true_answers) == 1: # TEXT_FILL
            text_answer = true_answers[0][1]

            if text_answer == solutions['text_answer']:
                return True
            
            return False
        elif len(all_answers) > 1 and len(true_answers) == 1: # MULTIPLE_CHOICE
            true_answer_id = true_answers[0][0]

            if true_answer_id == solutions['multiple_choice_answer']:
                return True
            
            return False
        elif len(all_answers) > 2 and len(true_answers) > 2:
            list_true_answer_ids = [item[0] for item in true_answers]

            if set(list_true_answer_ids) == set(solutions['checkboxes_answer']):
                return True
            
            return False
        else:
            return False
    except:
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()