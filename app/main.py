import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from app.models import GenerateRequest, GenerateResponse, GenericResponse, Provider
from app.session_manager import SessionManager

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("LLM-API")

# Initialize Singleton Manager
manager = SessionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Executes on Container Startup.
    Triggers parallel login sequences.
    """
    logger.info("--- SERVICE STARTING ---")
    
    # Run the parallel startup (it waits for all browsers to close before continuing)
    await manager.start_providers()
    
    yield
    
    logger.info("--- SERVICE SHUTTING DOWN ---")

app = FastAPI(title="LLM Session Service", lifespan=lifespan)

@app.get("/health")
def health_check():
    return {"status": "ok", "providers": list(manager.workers.keys())}

@app.post("/generate", response_model=GenerateResponse)
async def generate_content(payload: GenerateRequest):
    try:
        provider_key = payload.provider.value
        logger.info(f"Request: {provider_key}")
        
        response = await manager.generate(provider_key, payload.prompt)
        
        return GenerateResponse(
            provider=provider_key, 
            status=response["status"],
            mode=response["mode"],
            result=response["result"]
        )

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Request Failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Automation failed: {str(e)}"
        )

@app.delete("/session/{provider}", response_model=GenericResponse)
async def delete_session(provider: Provider):
    """
    Closes the specific provider's browser.
    """
    try:
        await manager.reset_provider(provider.value)
        return GenericResponse(message=f"{provider.value} browser closed.")
            
    except Exception as e:
        logger.error(f"Failed to close session: {e}")
        raise HTTPException(status_code=500, detail=str(e))