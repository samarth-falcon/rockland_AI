from fastapi import FastAPI
from app.api.endpoints import router as sip_router
import uvicorn

app = FastAPI()

app.include_router(sip_router, prefix="/sip", tags=["sip_calls"])


if __name__ == "__main__":
    uvicorn.run(
        "main:app",   # file_name:app_instance
        host="0.0.0.0",
        port=8000,
        reload=True   # optional (dev only)
    )