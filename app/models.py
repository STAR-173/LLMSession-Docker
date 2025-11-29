from pydantic import BaseModel, Field
from typing import List, Union, Optional

class GenerateRequest(BaseModel):
    # Polymorphic field: Accept String (Single) OR List[String] (Chain)
    prompt: Union[str, List[str]] = Field(
        ..., 
        description="Send a string for a single prompt, or a list of strings for a chained conversation."
    )

class GenerateResponse(BaseModel):
    status: str
    mode: str  # "single" or "chain"
    result: Union[str, List[str]]
    session_id: str = "default"

class GenericResponse(BaseModel):
    message: str
