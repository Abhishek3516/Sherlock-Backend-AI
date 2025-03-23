from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from fastapi.middleware import Middleware
from routers import apis
import logging

logger = logging.getLogger(__name__)

middleware = [Middleware(
            CORSMiddleware, 
            allow_origins=['*'], 
            allow_credentials=True, 
            allow_methods=['*'], 
            allow_headers=['*'])
        ]

app = FastAPI(middleware=middleware)
app.include_router(apis.router)