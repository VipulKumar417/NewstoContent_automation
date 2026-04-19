import requests
import logging
import urllib.parse
from config import NUMBEO_API_KEY

logger = logging.getLogger(__name__)

def fetch_cost_of_living(city_name: str) -> str | None:
    """
    Fetches the cost of living for a specific city from Numbeo API.
    Returns a short formatted string summarizing major costs, or None if failed.
    """
    if not NUMBEO_API_KEY or NUMBEO_API_KEY.startswith("your_"):
        logger.warning("Numbeo API key not configured. Skipping cost of living fetch.")
        return None

    try:
        # Encode the city string for the URL
        query = urllib.parse.quote(city_name)
        url = f"https://www.numbeo.com/api/city_prices?api_key={NUMBEO_API_KEY}&query={query}"
        
        headers = {"User-Agent": "Mozilla/5.0 (EpiCred Content Bot)"}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            logger.error(f"Numbeo API error: {response.status_code} - {response.text}")
            return None
            
        data = response.json()
        
        if "error" in data:
            logger.error(f"Numbeo returned an error: {data['error']}")
            return None
            
        if "prices" not in data or not data["prices"]:
            logger.warning(f"No price data found for city: {city_name}")
            return None
            
        # Extract meaningful datapoints
        currency = data.get("currency", "USD")
        
        # Numbeo Item ID references:
        # 26: Meal, Inexpensive Restaurant
        # 105: Apartment (1 bedroom) in City Centre
        # 106: Apartment (1 bedroom) Outside of Centre
        # 101: Basic (Electricity, Heating, Cooling, Water, Garbage) for 85m2 Apartment
        
        prices_dict = {item.get("item_id"): item.get("average_price") for item in data["prices"]}
        
        meal = prices_dict.get(26)
        rent_city = prices_dict.get(105)
        rent_outside = prices_dict.get(106)
        utilities = prices_dict.get(101)
        
        parts = [f"City: {data.get('name', city_name)}"]
        if rent_city:
            parts.append(f"1BR Rent (City Center): {rent_city:.2f} {currency}")
        if rent_outside:
            parts.append(f"1BR Rent (Suburbs): {rent_outside:.2f} {currency}")
        if meal:
            parts.append(f"Inexpensive Meal: {meal:.2f} {currency}")
        if utilities:
            parts.append(f"Basic Utilities: {utilities:.2f} {currency}")
            
        if len(parts) > 1:
            summary = " | ".join(parts)
            logger.info(f"Numbeo Data fetched: {summary}")
            return summary
            
        return None
        
    except Exception as e:
        logger.error(f"Failed to fetch cost of living from Numbeo for {city_name}: {e}")
        return None
