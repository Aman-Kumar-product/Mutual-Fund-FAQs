from pydantic import BaseModel, Field

class AskRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)

class Source(BaseModel):
    name: str | None = None
    url: str | None = None
    ingested_at: str | None = None

class AskResponse(BaseModel):
    answer: str
    sources: list[Source] | None = None
    refused: bool
