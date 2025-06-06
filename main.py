from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import checker_router, users_router
from pydantic import BaseModel
import uvicorn

class HealthResponse(BaseModel):
    status: str

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

prefix = "/api/v1"

app.include_router(checker_router, prefix=f"{prefix}", tags=["checker"])
app.include_router(users_router, prefix=f"{prefix}", tags=["auth"])

@app.get("/", response_model=HealthResponse)
async def health():
    return HealthResponse(status="Ok")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=1516, log_level="info")