"""
Location detection utilities for tools.
Uses IP geolocation similar to Django IPTrackingMiddleware.
"""
import logging
from typing import Dict, Any, Optional

import httpx
from fastapi import Request

logger = logging.getLogger(__name__)

# IP geolocation API (free, no key required)
IP_API_URL = "https://ip-api.com/json/{ip}?fields=status,message,continent,continentCode,country,countryCode,region,regionName,city,district,zip,lat,lon,timezone,currency,isp,org,as,mobile,query"

# Server IP cache (to avoid repeated lookups)
_server_ip_cache: Optional[str] = None


def get_client_ip(request: Request) -> str:
    """Extract client IP address from FastAPI request."""
    # Check X-Forwarded-For header (for proxies/load balancers)
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        # Fallback to direct client IP
        ip = request.client.host if request.client else "unknown"

    return ip


def is_private_ip(ip: str) -> bool:
    """Check if IP is private/localhost."""
    if not ip or ip == "unknown":
        return True

    # Localhost
    if ip in ["127.0.0.1", "localhost", "::1"]:
        return True

    # Private IP ranges
    if ip.startswith("192.168.") or ip.startswith("10."):
        return True

    # Check 172.16.0.0/12 range (172.16.x.x to 172.31.x.x)
    if ip.startswith("172."):
        try:
            parts = ip.split(".")
            if len(parts) >= 2:
                second_octet = int(parts[1])
                if 16 <= second_octet <= 31:
                    return True
        except (ValueError, IndexError):
            pass

    return False


async def get_server_public_ip() -> Optional[str]:
    """
    Get the server's public IP address.
    Uses a simple IP lookup service.

    Returns:
        Server's public IP address or None on error
    """
    global _server_ip_cache

    # Return cached IP if available
    if _server_ip_cache:
        return _server_ip_cache

    try:
        # Use a simple IP lookup service
        async with httpx.AsyncClient(timeout=3.0) as client:
            # Try ipify first (simple and reliable)
            response = await client.get("https://api.ipify.org?format=json")
            if response.status_code == 200:
                data = response.json()
                ip = data.get("ip")
                if ip:
                    _server_ip_cache = ip
                    logger.info(f"Server public IP detected: {ip}")
                    return ip

            # Fallback to icanhazip
            response = await client.get("https://icanhazip.com", headers={"Accept": "text/plain"})
            if response.status_code == 200:
                ip = response.text.strip()
                if ip:
                    _server_ip_cache = ip
                    logger.info(f"Server public IP detected: {ip}")
                    return ip
    except Exception as e:
        logger.warning(f"Failed to get server public IP: {str(e)}")

    return None


async def retrieve_ip_information(ip: str) -> Dict[str, Any]:
    """
    Determine location information for an IP address using ip-api.com.
    Similar to Django middleware _retrieve_ip_information method.

    Args:
        ip: IP address to look up

    Returns:
        Dict with location information or empty dict on error
    """
    # Skip private IPs
    if is_private_ip(ip):
        logger.debug(f"Skipping IP geolocation for private IP: {ip}")
        return {}

    try:
        url = IP_API_URL.format(ip=ip)

        async with httpx.AsyncClient(timeout=3.0) as client:  # 3 second timeout
            response = await client.get(url)

            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    logger.info(
                        f"Successfully retrieved location for IP {ip}: {data.get('city')}, {data.get('country')}")
                    return data
                else:
                    logger.warning(
                        f"IP API failed for {ip}: {data.get('message', 'Unknown error')}")
            else:
                logger.warning(
                    f"IP API HTTP error for {ip}: {response.status_code}")

        return {}

    except httpx.TimeoutException:
        logger.error(f"Timeout getting IP info for {ip}")
        return {}
    except httpx.RequestError as e:
        logger.error(f"Request error getting IP info for {ip}: {str(e)}")
        return {}
    except Exception as e:
        logger.error(f"Error getting IP info for {ip}: {str(e)}")
        return {}


async def get_location_from_ip(ip_address: str) -> Dict[str, Any]:
    """
    Get location information from IP address.
    If IP is localhost/private, uses server's public IP instead.

    Args:
        ip_address: IP address to look up

    Returns:
        Dict with location info (country, city, lat, lon, etc.)
    """
    # If IP is private/localhost, use server's public IP
    if is_private_ip(ip_address):
        logger.info(
            f"Client IP {ip_address} is private/localhost, using server IP instead")
        server_ip = await get_server_public_ip()
        if server_ip:
            ip_address = server_ip
        else:
            logger.warning(
                "Could not get server public IP, using localhost IP (may return empty location)")

    return await retrieve_ip_information(ip_address)


def extract_location_string(ip_info: Dict[str, Any]) -> Optional[str]:
    """
    Extract a location string from IP info for weather API.
    Prioritizes city, then region, then country.

    Args:
        ip_info: IP information dict from retrieve_ip_information

    Returns:
        Location string (e.g., "New York, US" or "London, GB") or None
    """
    if not ip_info:
        return None

    city = ip_info.get("city", "")
    country_code = ip_info.get("countryCode", "")

    if city and country_code:
        return f"{city},{country_code}"
    elif city:
        return city
    elif country_code:
        return country_code

    return None


def get_country_from_ip_info(ip_info: Dict[str, Any]) -> tuple:
    """
    Extract country information from IP info dictionary.

    Args:
        ip_info: IP information dict from retrieve_ip_information

    Returns:
        Tuple of (country, country_code, continent, continent_code)
    """
    country = ip_info.get("country", "")
    country_code = ip_info.get("countryCode", "")
    continent = ip_info.get("continent", "")
    continent_code = ip_info.get("continentCode", "")

    return country, country_code, continent, continent_code
