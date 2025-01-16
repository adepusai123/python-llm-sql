
from pydantic import BaseModel

class State(BaseModel):
    question: str
    query: str
    result: str
    answer: str

class QueryOutput(BaseModel):
    """Generated SQL query."""
    query: str


# Define state model for tracking the conversation UI only
# class ChatState(BaseModel):
#     question: str
#     query: str
#     result: str
#     answer: str