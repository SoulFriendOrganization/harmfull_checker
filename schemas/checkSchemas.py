from pydantic import BaseModel, field_validator

class CheckRequest(BaseModel):
    url: str

    @field_validator('url')
    def validate_url(cls, v: str) -> str:
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v