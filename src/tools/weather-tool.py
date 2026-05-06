import os
import requests
from langchain.tools import tool
from dotenv import load_dotenv
from datetime import datetime

load_dotenv('../../.env')

def get_city_lat_lon(city: str, country: str = None, api_key: str = None):
    url = "http://api.openweathermap.org/geo/1.0/direct"
    
    query = f"{city},{country}" if country else city
    
    params = {
        "q": query,
        "limit": 1,
        "appid": api_key
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        if not data:
            return None

        location = data[0]
        return {
            "lat": location.get("lat"),
            "lon": location.get("lon"),
            "name": location.get("name"),
            "country": location.get("country")
        }
    except requests.exceptions.RequestException as e:
        print(f"Error fetching geocode: {e}")
        return None

@tool
def get_current_weather(city: str, country: str = None):
    """
    Retrieves real-time weather information for a specified location.
    
    Use this tool when the user asks about current weather conditions, temperature, 
    or atmospheric states (like rain, sun, or clouds).
    
    Args:
        city (str): The name of the city to search for (e.g., 'London', 'Tokyo'). 
            Do not include the country name here; use the country argument instead.
        country (str, optional): The 2-letter ISO country code (e.g., 'US', 'GB', 'FR'). 
            Providing this helps disambiguate cities with the same name in different countries.
            
    Returns:
        dict: A dictionary containing status, city name, country, temperature (Celsius), 
              weather description, humidity, and wind speed.
    """
    api_key = os.getenv("WEATHER_API_KEY")
    
    lat_lon_data = get_city_lat_lon(city=city, country=country, api_key=api_key)

    if not lat_lon_data:
        return {
            "status": "error",
            "message": f"Could not find coordinates for {city}.",
            "city": city
        }
    
    lat, lon = lat_lon_data["lat"], lat_lon_data["lon"]

    params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "units": "metric"
    }

    try:
        response = requests.get("https://api.openweathermap.org/data/2.5/weather", params=params)
        response.raise_for_status()
        data = response.json()
        
        return {
            "status": "success",
            "city": data.get("name"),
            "country": data.get("sys", {}).get("country"),
            "temperature": f"{data['main']['temp']}°C",
            "feels_like": f"{data['main']['feels_like']}°C",
            "humidity": f"{data['main']['humidity']}%",
            "description": data['weather'][0]['description'],
            "wind_speed": f"{data['wind']['speed']} m/s"
        }

    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "message": str(e),
            "city": city
        }

@tool
def get_3_day_forecast(city: str, country: str = None):
    """
    Retrieves a 3-day weather forecast for a specific city.
    Use this tool when users ask about future weather, weekend plans, or 'the next few days'.
    
    Args:
        city (str): The name of the city.
        country (str, optional): 2-letter country code (ISO 3166).
    """
    api_key = os.getenv("WEATHER_API_KEY")
    lat_data = get_city_lat_lon(city=city, country=country, api_key=api_key)

    if not lat_data:
        return {"status": "error", "message": f"Location '{city}' not found."}
    
    lat, lon = lat_data["lat"], lat_data["lon"]

    url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "units": "metric"
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        forecast_list = []
        seen_dates = set()

        for entry in data.get("list", []):
            dt_object = datetime.fromtimestamp(entry["dt"])
            date_str = dt_object.strftime("%Y-%m-%d")
            hour = dt_object.hour

            if date_str not in seen_dates and hour >= 12:
                forecast_list.append({
                    "date": date_str,
                    "temp": f"{entry['main']['temp']}°C",
                    "description": entry['weather'][0]['description'],
                    "humidity": f"{entry['main']['humidity']}%"
                })
                seen_dates.add(date_str)
            
            if len(forecast_list) == 3:
                break

        return {
            "status": "success",
            "city": lat_data["name"],
            "country": lat_data["country"],
            "forecast": forecast_list
        }

    except requests.exceptions.RequestException as e:
        
        return {
            "status": "error",
            "message": str(e)
        }