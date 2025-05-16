from config import OPERATORS

def is_operator(user_id: int) -> bool:
    return user_id in OPERATORS
