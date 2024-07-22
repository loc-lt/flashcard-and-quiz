import re
import validators
import uuid

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
        if answer['is_correct']:
            count += 1
    return count
