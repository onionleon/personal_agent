import os
from dotenv import load_dotenv
from datetime import datetime
from typing import Literal
from langgraph.graph import END
from langchain_core.messages import SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from tools.weather_tool import get_current_weather, get_3_day_forecast
from tools.calendar_tool import add_event_to_calendar
from tools.email_tool import send_email
from tools.perplexity_tool import domain_perplexity_search, general_perplexity_search

load_dotenv()
model = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite",
    api_key=os.getenv("GEMINI_API_KEY")
)
tools = [
    get_current_weather, get_3_day_forecast, add_event_to_calendar, 
    send_email, domain_perplexity_search, general_perplexity_search
]
model_with_tools = model.bind_tools(tools)

def get_system_prompt():
    now = datetime.now().strftime("%A, %B %d, %Y %I:%M %p")
    return SystemMessage(content=f"""
        You are a highly capable Personal Executive Assistant.
        Your current local time is {now}. 
        
        GUIDELINES:
        1. For any scheduling request, always use the 'add_event_to_calendar' tool.
        2. If the user is vague about time (e.g., 'tomorrow'), use your internal knowledge 
           and the current reference time provided above to calculate the date.
        3. When sending emails, be professional and concise, do not reveal personal information.
        4. Before calling the 'send_email' or 'add_event_to_calendar' tools, 
           ensure you have all required arguments.
    """)

def llm_call(state: dict):
    """
    The main LLM node. It takes the current state, 
    prepends the system prompt, and calls the model.
    """
    messages = state["messages"]
    
    full_prompt = [get_system_prompt()] + messages
    
    response = model_with_tools.invoke(full_prompt)
    
    return {
        "messages": [response],
        "llm_calls": state.get('llm_calls', 0) + 1 
    }

def should_continue(state: dict) -> Literal["tools", "__end__"]:
    """
    Check the last message in the state. 
    If the LLM generated tool_calls, route to the 'tools' node.
    Otherwise, end the conversation and respond to the user.
    """
    messages = state.get("messages", [])
    
    if not messages:
        return "__end__"

    last_message = messages[-1]

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools" 

    # Otherwise, we are done
    return "__end__"
