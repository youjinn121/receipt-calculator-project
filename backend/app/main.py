from fastapi import FastAPI

import backend.app.db.base
from backend.app.api.receipt import router as receipt_router
from backend.app.db.base_class import Base
from backend.app.db.database import engine

app = FastAPI(
    title="Receipt Calculator API",
    version="0.1.0",
)

Base.metadata.create_all(bind=engine)

app.include_router(receipt_router)

@app.get("/")
def root():
    return {"message": "Receipt API is running"}