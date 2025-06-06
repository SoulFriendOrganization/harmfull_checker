from fastapi import HTTPException, status, Depends
import jwt
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv
from os import getenv
load_dotenv()

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/login")

def get_user_id(token: str = Depends(oauth2_scheme)) -> str:
    """
    Extracts the user ID from the JWT token.
    
    :param token: JWT token
    :return: User ID extracted from the token
    :raises HTTPException: If the token is invalid or expired
    """
    try:
        payload = jwt.decode(token, getenv("SECRET_KEY_ENCRYPTION"), algorithms=["HS256"])
        if "user_id" not in payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,               
                detail="Could not validate credentials", 
                headers={"WWW-Authenticate": "Bearer"}
                )
        return payload.get("user_id")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")