from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP
import time
import os
import jwt
from dotenv import load_dotenv
import logging
import asyncio

# Load environment variables from .env file
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("PC entities")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("log.txt")]
)

# Constants
USER_AGENT = "offer-fetcher/1.0"
BASE_URL = os.getenv("DNO_HOST", "https://dc83-api-pub.lotusflare.com")

def get_dno_bearer_token(operator_name: str = "smartless", portal_id: str = "13") -> str:
    epoch = int(time.time())
    payload = {
        "epoch": epoch,
        "key_id": os.getenv("DNO_TOKEN_KEY_ID"),
        "operator_name": operator_name,
        "type": 1,
        "version": 1,
        "portal_id": portal_id
    }
    headers = { "alg": "HS256", "typ": "JWT" }
    secret_key = os.getenv("DNO_TOKEN_KEY", "")
    token = jwt.encode(payload, secret_key, algorithm="HS256", headers=headers)
    logging.info(f"Generated bearer token for operator: {operator_name}")
    return f"Bearer {token}"

VALID_ENTITY_TYPES = {"offer", "product", "service"}

async def fetch_offers(operator_name: str = "smartless", entity_type: str = "offer"):
    if entity_type not in VALID_ENTITY_TYPES:
        raise ValueError(f"Invalid entity_type: {entity_type}. Must be one of: {', '.join(VALID_ENTITY_TYPES)}")
    logging.info(f"📡 Starting offer fetch for operator: {operator_name}")
    token = get_dno_bearer_token(operator_name)
    headers = {
        "Authorization": token,
        "User-Agent": USER_AGENT,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    body = {
        "option": {
            "include_referenced_entities": True
        }
    }

    url = f"{BASE_URL}/api/v3/catalog/{entity_type}/get"
    try:
        logging.info(f"Making request to: {url}")
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=body, headers=headers, timeout=30.0)
            response.raise_for_status()
            logging.info(f"✅ Response status: {response.status_code}")
            data = response.json()
            logging.info("Response data received successfully")
            return data, response
    except httpx.HTTPError as e:
        logging.error(f"❌ Request failed: {e}")
        return None, e

async def fetch_pricing_rules(operator_name: str = "smartless") -> tuple[dict | None, httpx.Response | Exception]:
    logging.info(f"📡 Starting pricing rules fetch for operator: {operator_name}")
    token = get_dno_bearer_token(operator_name)
    headers = {
        "Authorization": token,
        "User-Agent": USER_AGENT,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    url = f"{BASE_URL}/api/v3/pricing/pricing_rule"
    try:
        logging.info(f"Making request to: {url}")
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            logging.info(f"✅ Response status: {response.status_code}")
            data = response.json()
            logging.info("Response data received successfully")
            return data, response
    except httpx.HTTPError as e:
        logging.error(f"❌ Request failed: {e}")
        return None, e


@mcp.tool()
async def get_offers(operator_name: str, entity_type: str = "offer") -> dict:
    """Fetch catalog entities from the DNO API.
    
    Args:
        operator_name (str): Name of the operator
        entity_type (str): Type of entity to fetch. Must be one of: 'offer', 'product', 'service'
    """    
    data, response = await fetch_offers(operator_name, entity_type)

    if not data:
        return {"error": f"Unable to fetch offers for operator: {operator_name} {response}", "success": False}

    return {"data": data, "success": True}

@mcp.tool()
async def get_pricing_rules(operator_name: str) -> dict:
    """Fetch pricing rules from the DNO API.
    
    Args:
        operator_name (str): Name of the operator
    """    
    data, response = await fetch_pricing_rules(operator_name)

    if not data:
        return {"error": f"Unable to fetch pricing rules for operator: {operator_name} {response}", "success": False}

    return {"data": data, "success": True}

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')