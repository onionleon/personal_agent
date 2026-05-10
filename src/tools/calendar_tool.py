import os
import datetime
import os.path
from dateutil import parser
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from langchain.tools import tool

load_dotenv("../../.env")

SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    credentials_file_path = os.getenv("CREDENTIALS_FILE_PATH")
    credentials = None
    if os.path.exists('token.json'):
        credentials = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file_path, SCOPES)
            credentials = flow.run_local_server(port=0)
    
        with open('token.json', 'w') as token:
            token.write(credentials.to_json())

    return build('calendar', 'v3', credentials=credentials)

def transform_relative_date(relative_date_string: str):
    now = datetime.datetime.now()
    
    try:
        parsed_date = parser.parse(relative_date_string, default=now, fuzzy=True)
        return {
            "status": "success",
            "parsed_iso": parsed_date.isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@tool
def add_event_to_calendar(event_name: str, event_start_date: str, event_end_date: str, event_location: str, timezone: str = "UTC"):
    """
    Creates a new event on the user's primary Google Calendar.
    Use this tool when the user wants to schedule a meeting, set a reminder, or add an appointment.
    The tool requires specific ISO 8601 timestamps. If the user provides relative time
    (e.g., 'tomorrow at 5pm'), you must calculate the exact date and time based on the
    current date before calling this tool.

    Args:
        event_name (str): A concise summary or title of the event.
        event_start_date (str): The start date and time in ISO 8601 format (YYYY-MM-DDTHH:MM:SS).
        Example: '2024-05-28T09:00:00'.
        event_end_date (str): The end date and time in ISO 8601 format (YYYY-MM-DDTHH:MM:SS).
        Must be chronologically after the start date.
        event_location (str): The physical address or meeting link (e.g., 'Zoom', '123 Main St').
        If not specified, use 'Not Specified'.
        timezone (str): The IANA Time Zone string (e.g., 'America/New_York', 'Europe/London').
        Defaults to 'UTC'. Ensure this matches the user's local context.

    Returns:
        dict: A dictionary containing the 'status' (success/error), a confirmation message,
        and the HTML link to the created event.
    """

    start_result = transform_relative_date(event_start_date)
    if start_result["status"] == "error":
        return {
            "status": "error",
            "message": f"Start date error: {start_result['message']}. Please provide a clearer date."
        }

    end_result = transform_relative_date(event_end_date)
    if end_result["status"] == "error":
        return {
            "status": "error",
            "message": f"End date error: {end_result['message']}. Please provide a clearer date."
        }

    iso_start = start_result["parsed_iso"]
    iso_end = end_result["parsed_iso"]

    try:
        service = get_calendar_service()
        event = {
            'summary': event_name,
            'location': event_location,
            'start': {'dateTime': iso_start, 'timeZone': timezone},
            'end': {'dateTime': iso_end, 'timeZone': timezone},
        }

        event_result = service.events().insert(calendarId='primary', body=event).execute()
        return {
            "status": "success",
            "message": f"Event '{event_name}' created successfully.",
            "link": event_result.get('htmlLink')
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Calendar API Error: {str(e)}"
        }

@tool
def get_events_upcoming_week():
    """
    Retrieves all scheduled events from the user's primary Google Calendar for the next 7 days.
    Use this tool when the user asks 'What does my week look like?', 'Am I busy tomorrow?', 
    or 'Do I have any meetings coming up?'.
    """
    now = datetime.datetime.utcnow().isoformat() + 'Z' 
    end_date = (datetime.datetime.utcnow() + datetime.timedelta(days=7)).isoformat() + 'Z'

    try:
        service = get_calendar_service()
        events_result = service.events().list(
            calendarId='primary',
            timeMin=now,
            timeMax=end_date,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
    except Exception as e:
        return {
            "status": "error",
            "message": f"Calendar API Error: {str(e)}"
        }

    events = events_result.get('items', [])

    if not events:
        return {
            "status": "success",
            "message": "No upcoming events found for the next week.",
            "events": []
        }

    formatted_events = []
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        end = event['end'].get('dateTime', event['end'].get('date'))
        
        readable_start = start.replace('T', ' ').replace('Z', '')[:16]

        formatted_events.append({
            "summary": event.get('summary', 'No Title'),
            "start": readable_start,
            "location": event.get('location', 'No location specified'),
            "description": event.get('description', ''),
            "link": event.get('htmlLink')
        })

    return {
        "status": "success",
        "count": len(formatted_events),
        "events": formatted_events
    }