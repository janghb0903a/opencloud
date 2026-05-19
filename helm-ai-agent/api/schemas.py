from pydantic import BaseModel, Field, validator
from typing import List

class ChartFile(BaseModel):
    path: str
    content: str

class ChartResponse(BaseModel):
    chart_name: str = Field(min_length=1)
    files: List[ChartFile]

    @validator("files")
    def non_empty_files(cls, v):
        if not v:
            raise ValueError("files must not be empty")
        return v
