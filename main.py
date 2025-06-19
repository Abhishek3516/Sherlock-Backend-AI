from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from fastapi.middleware import Middleware
from routers import apis
import logging
from src.controller.controller import auth_router
from src.types.custom_application_error import CustomApplicationError
from fastapi.openapi.utils import get_openapi

logger = logging.getLogger(__name__)

middleware = [Middleware(
            CORSMiddleware, 
            allow_origins=['*'], 
            allow_credentials=True, 
            allow_methods=['*'], 
            allow_headers=['*'])
        ]

# Define security scheme for Bearer token
security = HTTPBearer()

app = FastAPI(middleware=middleware)
app.include_router(apis.router)
app.include_router(auth_router)

@app.exception_handler(CustomApplicationError)
async def custom_exception_handler(request, exc: CustomApplicationError):
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.message  # Already a dict if from model_dump()
    )


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    # Add BearerAuth security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter your AWS Cognito JWT token in the format 'Bearer <token>'."
        }
    }
    # Apply security to all endpoints
    for path in openapi_schema["paths"]:
        for method in openapi_schema["paths"][path]:
            openapi_schema["paths"][path][method]["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi