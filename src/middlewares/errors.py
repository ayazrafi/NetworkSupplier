import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "details": None
        }
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Extract readable field names and messages from Pydantic errors
    details = []
    for error in exc.errors():
        loc = " -> ".join(str(x) for x in error.get("loc", []))
        msg = error.get("msg", "Validation error")
        details.append(f"{loc}: {msg}")
    
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "error": "Validation error",
            "details": details
        }
    )

async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(f"Global Exception caught: {exc}", exc_info=True)
    
    # Handle duplicate key error from MongoDB if available
    err_str = str(exc)
    if "duplicate key error" in err_str or "E11000" in err_str:
        return JSONResponse(
            status_code=409,
            content={
                "success": False,
                "error": "Duplicate key error - Record already exists",
                "details": err_str
            }
        )
        
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Server error",
            "details": err_str
        }
    )
