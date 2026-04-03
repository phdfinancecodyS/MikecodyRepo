"""Entry point — start the CCE API server via uvicorn."""
import os
import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("CCE_PORT", "8000"))
    log_level = os.getenv("CCE_LOG_LEVEL", "info").lower()
    uvicorn.run(
        "src.app:app",
        host="0.0.0.0",
        port=port,
        log_level=log_level,
        reload=False,
    )
