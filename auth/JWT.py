import jwt
from datetime import datetime, timedelta
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

# Import configuration
from config import config

security = HTTPBearer()

def generate_token(data: dict) -> str:
    """Generate a JWT token with expiration"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=config.JWT_EXPIRATION_HOURS)
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access_token"
    })
    encoded_jwt = jwt.encode(to_encode, config.JWT_SECRET_KEY, algorithm=config.JWT_ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> str:
    """Verify a JWT token and return the username"""
    try:
        payload = jwt.decode(token, config.JWT_SECRET_KEY, algorithms=[config.JWT_ALGORITHM])
        username: str = payload.get("username")
        token_type: str = payload.get("type")
        
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token: missing username")
        
        if token_type != "access_token":
            raise HTTPException(status_code=401, detail="Invalid token type")
            
        return username
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token verification failed: {str(e)}")

def get_current_teacher(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Get current authenticated teacher (required authentication)"""
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    token = credentials.credentials
    return verify_token(token)

def get_current_teacher_optional(request: Request) -> Optional[str]:
    """
    Optional authentication that supports both Authorization header and token query parameter.
    Returns the username if authenticated, None if not authenticated.
    Raises HTTPException only for invalid tokens, not for missing tokens.
    """
    token = None
    
    # Try to get token from Authorization header first
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]  # Remove "Bearer " prefix
    
    # If no header token, try query parameter
    if not token:
        token = request.query_params.get("token")
    
    # If no token found, return None (not authenticated)
    if not token:
        return None
    
    # Verify the token - this will raise HTTPException for invalid tokens
    return verify_token(token)

def create_access_token(username: str, additional_claims: dict = None) -> str:
    """Create an access token with optional additional claims"""
    data = {"username": username}
    if additional_claims:
        data.update(additional_claims)
    return generate_token(data)

def decode_token_payload(token: str) -> dict:
    """Decode token payload without verification (for debugging)"""
    try:
        # Decode without verification for inspection
        payload = jwt.decode(token, options={"verify_signature": False})
        return payload
    except Exception as e:
        return {"error": str(e)}
