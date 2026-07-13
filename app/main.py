import os
import contextlib
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from app.config.settings import settings
from app.config.redis import get_redis_client
from app.config.logging import logger
from app.core.utils.exceptions import STSException
from app.core.utils.responses import current_lang, make_response
from app.core.websocket.manager import manager
from app.routers import auth_router, public_router, health_router, student_router, teacher_router, ai_engine_router

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup and shutdown configurations."""
    logger.info("Initializing STS Gateway Backend Application Startup lifespans.")
    
    # Establish Redis pub/sub listener thread for WebSocket broadcasting
    redis_client = get_redis_client()
    await manager.start_pubsub_listener(redis_client)
    
    yield
    
    logger.info("Starting shutdown teardown procedures.")
    await manager.stop_pubsub_listener()
    await redis_client.close()
    logger.info("Teardown procedures complete.")

# Initialize API Server
app = FastAPI(
    title=settings.APP_NAME,
    description="STS Shared Core Framework, Authentication Gateway, and Security System.",
    version="1.0.0",
    lifespan=lifespan
)

# Apply CORS configurations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dynamic language preference extractor middleware
@app.middleware("http")
async def extract_language_preference(request: Request, call_next):
    # Attempt to extract preferred language from query parameters first, then Accept-Language header
    lang = request.query_params.get("lang")
    if not lang:
        accept_lang = request.headers.get("accept-language", "")
        if accept_lang:
            lang = accept_lang.split(",")[0].split("-")[0]
            
    if lang in ["ar", "en"]:
        current_lang.set(lang)
    else:
        current_lang.set(settings.DEFAULT_LANG)
        
    response = await call_next(request)
    return response

# Standard mounting of media upload folders for local testing
if settings.USE_LOCAL_STORAGE:
    os.makedirs(settings.LOCAL_STORAGE_DIR, exist_ok=True)
    app.mount("/static", StaticFiles(directory=settings.LOCAL_STORAGE_DIR), name="static")

# Custom STS application error handler
@app.exception_handler(STSException)
async def sts_exception_handler(request: Request, exc: STSException):
    logger.warn("Application exception intercepted", code=exc.code, path=request.url.path)
    return JSONResponse(
        status_code=exc.status_code,
        content=make_response(
            success=False,
            code=exc.code,
            message=exc.message
        )
    )

# Generic system error handler
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled runtime exception encountered", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=make_response(
            success=False,
            code="INTERNAL_SERVER_ERROR",
            message=str(exc)
        )
    )

app.include_router(health_router, prefix=settings.API_V1_STR)
app.include_router(public_router, prefix=settings.API_V1_STR)
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(student_router, prefix=settings.API_V1_STR)
app.include_router(teacher_router, prefix=settings.API_V1_STR)
app.include_router(ai_engine_router, prefix=settings.API_V1_STR)

# Websocket active server endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint supporting real-time connection routing."""
    await manager.connect(websocket)
    try:
        while True:
            # Handle incoming data frames
            data = await websocket.receive_json()
            # Simple routing/echo example
            await manager.send_personal_message({"type": "echo", "payload": data}, websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error("Error in websocket connection loop", error=str(e))
        manager.disconnect(websocket)
