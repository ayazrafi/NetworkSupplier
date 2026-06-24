import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from src.config.environment import Environment

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=2)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, Environment.JWT_SECRET, algorithm="HS256")
    return encoded_jwt

def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        decoded_token = jwt.decode(token, Environment.JWT_SECRET, algorithms=["HS256"])
        return decoded_token
    except jwt.PyJWTError:
        return None
