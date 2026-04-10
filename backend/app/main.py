from fastapi import FastAPI

from backend.app.db.database import engine
from backend.app.db.base import Base

app = FastAPI(title="Receipt Calculator API", version="0.1.0")

# 앱 시작 시 테이블 생성
Base.metadata.create_all(bind=engine)


@app.get("/")
def root():
    return {"message": "Receipt Calculator API is running"}