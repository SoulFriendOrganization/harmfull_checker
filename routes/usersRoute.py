from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.orm import Session
from database.connection import get_db
from fastapi.security import OAuth2PasswordRequestForm
from logging_config import logger
from routes.auth import get_user_id
from database.models import UserAuth, User
from utils.auth import create_access_token, verify_password, get_password_hash

router = APIRouter()

def login_users(db: Session, username: str, password: str) -> str:
    """
    Log in a user by verifying the username and password.
    
    :param db: SQLAlchemy session object
    :param username: Username of the user
    :param password: Password of the user
    :return: UserAuth object if login is successful
    """
    try:
        logger.info(f"User login attempt with username: {username}")
        user_auth = db.query(UserAuth).filter(UserAuth.username == username).first()
        user_hashed_password = user_auth.password if user_auth else None
        if not user_auth or not verify_password(password, user_hashed_password):
            raise ValueError("Invalid username or password")
        access_token = create_access_token(data={"user_id": str(user_auth.user_id), "username": user_auth.username})
        return access_token
    except Exception as e:
        logger.error(f"Error during user login: {e}")
        raise ValueError("Login failed") from e
    

@router.post("/login", status_code=200)
def login_endpoint(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    response: Response = None
):
    """
    Endpoint to log in a user.

    :param form_data: Form data containing username and password
    :param db: SQLAlchemy session object
    :return: Response with access token
    """
    try:
        logger.info(f"User login attempt with username: {form_data.username}")
        access_token = login_users(db, form_data.username, form_data.password)
        if response is None:
            raise HTTPException(status_code=500, detail="Response object is required")
        response.set_cookie(
            key="token",
            value=access_token,
            httponly=True,
            secure=True,  
            samesite="Lax"  
        )
        return {"access_token": access_token, "token_type": "bearer"}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))