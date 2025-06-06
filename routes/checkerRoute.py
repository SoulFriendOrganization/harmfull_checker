from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.orm import Session
from database.connection import get_db
from logging_config import logger
from schemas.checkSchemas import CheckRequest
from utils.checker import harmful_checker 
from pydantic import BaseModel, Field
from routes.auth import get_user_id

router = APIRouter()

class HarmfulCheckerConfig(BaseModel):
    is_harmful: bool = Field(description="Indicates if the content is harmful (like online gambling or phising) or not.")
    summary_harmful: str = Field(description="Summary of the harmful content (hoax, phising, not safety, online gambling, pirating, virus) detected.")

@router.post("/check_harmful", status_code=200, response_model=HarmfulCheckerConfig)
def check_harmful_content(
    request: CheckRequest,
    user_id: str = Depends(get_user_id),  # Assuming get_user_id is defined in auth.py
    db: Session = Depends(get_db),
):
    """
    Endpoint to check if the content is harmful.
    
    :param request: Request object containing the content to be checked
    :param db: SQLAlchemy session object
    :return: Response indicating whether the content is harmful or not
    """
    try:
        logger.info(f"Checking harmful content: {request.url}")
        harmful_result = harmful_checker.harmful_checker(request.url)
        if harmful_result is None:
            logger.warning("No content found for harmful check.")
            return {"is_harmful": False, "summary_harmful": "No content to check."}
        return harmful_result
    except Exception as e:
        logger.error(f"Error checking harmful content: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")