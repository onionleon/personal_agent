import operator
from langchain.messages import AnyMessage
from typing_extensions import TypedDict, Annotated

class MessageState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    llm_calls: int