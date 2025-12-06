"""
Weather tool for getting weather information.
"""
import logging
from typing import Dict, Any, Optional

import httpx

from app.config import settings
from app.tools.base import BaseTool
from app.tools.location import (
    get_location_from_ip,
    extract_location_string
)

logger = logging.getLogger(__name__)

OPENWEATHERMAP_API_URL = "https://api.openweathermap.org/data/2.5/weather"


class WeatherTool(BaseTool):
    """Tool for getting weather information."""

    @property
    def name(self) -> str:
        return "get_weather"

    @property
    def description(self) -> str:
        return (
            "Get current weather information for a location. "
            "If no location is provided, attempts to use the user's location from their IP address. "
            "Location can be a city name (e.g., 'London'), city with country code (e.g., 'London,GB'), "
            "or coordinates (e.g., 'lat,lon'). "
            "Returns detailed weather data including temperature, conditions, humidity, wind speed, and pressure."
        )

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "location": {
                    "type": ["string", "null"],
                    "description": "Location name (city, city with country code, or coordinates). If not provided or empty, will attempt to use user's location from IP address."
                },
                "units": {
                    "type": "string",
                    "enum": ["metric", "imperial", "kelvin"],
                    "description": "Temperature units. Default is 'metric' (Celsius).",
                    "default": "metric"
                }
            },
            "required": []
        }

    async def execute(
            self,
            location: Optional[str] = None,
            units: str = "metric",
            ip_address: Optional[str] = None,
            **kwargs
    ) -> str:
        """
        Execute weather tool.

        Args:
            location: Location string (optional, will use IP if not provided)
            units: Temperature units (metric, imperial, kelvin)
            ip_address: User's IP address (from request context)
            **kwargs: Additional context

        Returns:
            Formatted weather information string
        """
        import time
        start_time = time.time()
        logger.info(
            f"[WEATHER_TOOL] Execution started - location: {location}, units: {units}, ip_address: {ip_address}")

        # Treat placeholder strings as empty
        if location and location.lower() in ["user's location", "user location", "my location", ""]:
            location = None
            logger.debug("[WEATHER_TOOL] Location was placeholder string, set to None")

        # If no location provided, try to get from IP
        if not location and ip_address:
            try:
                logger.info(f"[WEATHER_TOOL] Getting location from IP: {ip_address}")
                ip_start = time.time()
                ip_info = await get_location_from_ip(ip_address)
                ip_time = time.time() - ip_start
                logger.info(f"[WEATHER_TOOL] IP geolocation completed in {ip_time:.2f}s")
                location = extract_location_string(ip_info)

                if not location:
                    logger.warning(
                        f"[WEATHER_TOOL] Could not extract location from IP info: {ip_info}")
                    return "I couldn't determine your location automatically. Please provide a city name or location."
                logger.info(f"[WEATHER_TOOL] Location extracted from IP: {location}")
            except Exception as e:
                logger.error(f"[WEATHER_TOOL] Error getting location from IP: {str(e)}", exc_info=True)
                return "I couldn't determine your location from your IP address. Please provide a city name or location."

        if not location:
            logger.warning("[WEATHER_TOOL] No location provided and IP geolocation failed")
            return "Please provide a location (city name, coordinates, etc.) to get weather information."

        # Get weather data
        try:
            logger.info(f"[WEATHER_TOOL] Fetching weather data for location: {location}, units: {units}")
            weather_data = await self._fetch_weather(location, units)
            execution_time = time.time() - start_time
            logger.info(
                f"[WEATHER_TOOL] Weather data fetched successfully in {execution_time:.2f}s - location: {location}")
            formatted_response = self._format_weather_response(weather_data, units)
            total_time = time.time() - start_time
            logger.info(
                f"[WEATHER_TOOL] Execution completed successfully in {total_time:.2f}s - response_length: {len(formatted_response)}")
            return formatted_response
        except httpx.HTTPStatusError as e:
            execution_time = time.time() - start_time
            if e.response.status_code == 404:
                logger.warning(f"[WEATHER_TOOL] Location not found: {location} - time: {execution_time:.2f}s")
                return f"I couldn't find weather information for '{location}'. Please check the location name and try again."
            else:
                logger.error(
                    f"[WEATHER_TOOL] HTTP error fetching weather for {location}: {e.response.status_code} - time: {execution_time:.2f}s")
                return f"There was an error fetching weather data (HTTP {e.response.status_code}). Please try again later."
        except httpx.TimeoutException:
            execution_time = time.time() - start_time
            logger.error(f"[WEATHER_TOOL] Timeout fetching weather for {location} - time: {execution_time:.2f}s")
            return "The weather service is taking too long to respond. Please try again in a moment."
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                f"[WEATHER_TOOL] Error fetching weather for {location}: {str(e)} - time: {execution_time:.2f}s",
                exc_info=True)
            return f"Sorry, I encountered an error while fetching weather information: {str(e)}"

    async def _fetch_weather(self, location: str, units: str) -> Dict[str, Any]:
        """Fetch weather data from OpenWeatherMap API."""
        import time
        api_start = time.time()

        if not settings.openweathermap_api_key:
            logger.error("[WEATHER_TOOL] OpenWeatherMap API key not configured")
            raise ValueError("OpenWeatherMap API key not configured")

        params = {
            "q": location,
            "appid": settings.openweathermap_api_key,
            "units": units
        }

        logger.debug(f"[WEATHER_TOOL] Calling OpenWeatherMap API - location: {location}, units: {units}")
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(OPENWEATHERMAP_API_URL, params=params)
            api_time = time.time() - api_start
            logger.debug(f"[WEATHER_TOOL] API response received in {api_time:.2f}s - status: {response.status_code}")
            response.raise_for_status()
            return response.json()

    def _format_weather_response(self, data: Dict[str, Any], units: str) -> str:
        """Format weather data into a readable string."""
        city = data.get("name", "Unknown")
        country = data.get("sys", {}).get("country", "")
        location_str = f"{city}, {country}" if country else city

        main = data.get("main", {})
        weather = data.get("weather", [{}])[0]

        temp = main.get("temp", 0)
        feels_like = main.get("feels_like", 0)
        humidity = main.get("humidity", 0)
        pressure = main.get("pressure", 0)

        wind = data.get("wind", {})
        wind_speed = wind.get("speed", 0)
        wind_deg = wind.get("deg", 0)

        description = weather.get("description", "").title()
        condition = weather.get("main", "")

        # Unit symbols
        temp_unit = "°C" if units == "metric" else "°F" if units == "imperial" else "K"
        speed_unit = "m/s" if units == "metric" else "mph" if units == "imperial" else "m/s"

        # Wind direction
        wind_directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                           "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        wind_dir = wind_directions[int(
            (wind_deg % 360) / 22.5)] if wind_deg else "N/A"

        # Visibility
        visibility = data.get("visibility", 0)
        visibility_km = visibility / 1000 if visibility else 0

        # Format weather data clearly
        result = f"""Current weather for {location_str}:

🌡️ Temperature: {temp:.1f}{temp_unit} (feels like {feels_like:.1f}{temp_unit})
☁️ Conditions: {description} ({condition})
💧 Humidity: {humidity}%
💨 Wind: {wind_speed} {speed_unit} {wind_dir}
🔽 Pressure: {pressure} hPa"""

        if visibility_km > 0:
            result += f"\n👁️ Visibility: {visibility_km:.1f} km"

        return result
