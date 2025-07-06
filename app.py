from fastapi import FastAPI
from app.api.routes import coaches
from infrastructure.db.init_db import init_db
init_db()

app = FastAPI()

app.include_router(coaches.router)
