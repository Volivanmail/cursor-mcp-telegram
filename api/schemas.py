from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    user_id: str = Field(min_length=1, max_length=64)


class TaskRead(BaseModel):
    id: int
    title: str
    user_id: str
    done: bool
    created_at: str
