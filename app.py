from fastapi import FastAPI
from app.api.routes import coaches

app = FastAPI()

app.include_router(coaches.router)
