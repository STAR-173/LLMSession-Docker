import logging
import shutil
import os
import asyncio
from fastapi import FastAPI, HTTPException, status
from app.models import GenerateRequest, GenerateResponse, GenericResponse
from app.session_manager import SessionManager

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("LLM-API")

SESSION_DIR = "/root/.local/share/LLMSession"

app = FastAPI(title="LLM Session Service")

# Initialize Singleton Manager
manager = SessionManager()

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "llm-session-api"}

@app.post("/generate", response_model=GenerateResponse)
async def generate_content(payload: GenerateRequest):
    """
    Sends prompt to the persistent background browser.
    Context is maintained between requests.
    """
    try:
        creds = {
            "email": os.environ.get("CHATGPT_EMAIL"),
            "password": os.environ.get("CHATGPT_PASSWORD"),
            "method": "email" 
        }

        if not creds["email"] or not creds["password"]:
            raise HTTPException(status_code=500, detail="Missing credentials.")

        # Send to manager (waits for queue)
        response = await manager.generate(payload.prompt, creds)
        
        return GenerateResponse(**response)

    except Exception as e:
        logger.error(f"Request Failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Automation failed: {str(e)}"
        )

@app.delete("/session", response_model=GenericResponse)
async def delete_session():
    """
    Closes the current browser instance to free memory/reset state.
    Does NOT delete the persistent login cookies (session_data).
    """
    try:
        logger.info("Received request to close browser session...")
        
        # This will call bot.close() in the background thread
        # It closes the window/process but keeps the User Data Directory intact
        await manager.reset()

        return GenericResponse(message="Browser instance closed. Persistence files preserved.")
            
    except Exception as e:
        logger.error(f"Failed to close session: {e}")
        raise HTTPException(status_code=500, detail=str(e))
