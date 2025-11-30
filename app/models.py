from pydantic import BaseModel, Field, validator
from typing import List, Union, Optional
from enum import Enum

class Provider(str, Enum):
    CHATGPT = "chatgpt"
    CLAUDE = "claude"
    AISTUDIO = "aistudio"

class GenerateRequest(BaseModel):
    # Select which bot to use
    provider: Provider = Field(
        default=Provider.CHATGPT,
        description="The LLM provider to use (chatgpt, claude, aistudio)."
    )
    
    prompt: Union[str, List[str]] = Field(
        ..., 
        description="Send a string for a single prompt, or a list of strings for a chained conversation."
    )

class GenerateResponse(BaseModel):
    status: str
    provider: str
    mode: str
    result: Union[str, List[str]]

class GenericResponse(BaseModel):
    message: str
