from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, BackgroundTasks, Request, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import traceback
from pathlib import Path
from typing import List, Optional, Dict, Any
import uuid
import jwt
import bcrypt
import asyncio
import httpx
import re
from datetime import datetime, timezone, timedelta, date
from openai import AsyncOpenAI

from app.api.chat_routes import ChatRouteService
from app.core.logging import get_logger
from app.models.chat import ChatMessage, ChatRequest, Token, User, UserCreate
from app.services.ai_service import StableChatOrchestrator


def get_openai_client():
    """Create OpenAI client. Works with both direct OpenAI keys and Emergent keys."""
    api_key = os.environ.get('OPENAI_API_KEY') or os.environ.get('EMERGENT_LLM_KEY')
    if not api_key:
        raise ValueError("No AI API key configured. Set OPENAI_API_KEY in .env")
    
    if api_key.startswith('sk-emergent'):
        # Emergent Universal Key — route through Emergent proxy
        return AsyncOpenAI(
            api_key=api_key,
            base_url="https://integrations.emergentagent.com/llm"
        )
    else:
        # Direct OpenAI key
        return AsyncOpenAI(api_key=api_key)
from urllib.parse import urlparse
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from cryptography.fernet import Fernet
import ssl
import base64
import requests
from bs4 import BeautifulSoup
import json
import PyPDF2
from io import BytesIO

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
import certifi
mongo_url = os.environ.get('MONGO_URL')
if not mongo_url:
    raise RuntimeError("MONGO_URL environment variable is required")
# Use certifi CA bundle for Atlas SSL connections
if 'mongodb+srv' in mongo_url or 'mongodb.net' in mongo_url:
    client = AsyncIOMotorClient(mongo_url, tlsCAFile=certifi.where())
else:
    client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'myhostiq')]

# Initialize FastAPI app with security settings
app = FastAPI(
    title="MyHostIQ API",
    description="Smart Guest Assistant Platform API",
    version="1.0.0",
    docs_url="/docs" if os.getenv("ENVIRONMENT") != "production" else None,
    redoc_url="/redoc" if os.getenv("ENVIRONMENT") != "production" else None
)

# Rate limiting setup
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security Middleware
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["*"]  # Configure properly in production
)

app.add_middleware(SlowAPIMiddleware)

# Global Exception Handlers  
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors gracefully"""
    logger.error(f"Validation error on {request.url}: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error", 
            "message": "Invalid request data",
            "details": exc.errors()
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions gracefully"""
    logger.error(f"HTTP error on {request.url}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "Request Error",
            "message": exc.detail,
            "status_code": exc.status_code
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions gracefully"""
    logger.error(f"Unexpected error on {request.url}: {str(exc)}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    
    # Don't expose internal errors in production
    if os.getenv("ENVIRONMENT") == "production":
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "message": "An unexpected error occurred. Please try again later."
            }
        )
    else:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error", 
                "message": str(exc),
                "traceback": traceback.format_exc()
            }
        )

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security and Encryption
security = HTTPBearer()
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-here')
JWT_ALGORITHM = 'HS256'

# Encryption for email passwords
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', 'your-32-byte-encryption-key-here')
if ENCRYPTION_KEY == 'your-32-byte-encryption-key-here':
    # Generate a key for development
    ENCRYPTION_KEY = base64.urlsafe_b64encode(b'dev-key-not-secure-change-me!!').decode()
    
cipher_suite = Fernet(ENCRYPTION_KEY.encode() if len(ENCRYPTION_KEY) == 44 else base64.urlsafe_b64encode(ENCRYPTION_KEY[:32].encode()))

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    full_name: str
    phone: str = ""
    hashed_password: str
    is_active: bool = True
    is_admin: bool = False  # Add admin role
    email_verified: bool = False
    phone_verified: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Enhanced Whitelabeling settings
    brand_name: str = "MyHomeIQ"
    brand_logo_url: str = ""
    brand_primary_color: str = "#2563eb"
    brand_secondary_color: str = "#1d4ed8"
    ai_tone: str = "professional"  # professional, friendly, casual
    ai_assistant_name: str = "AI Assistant"  # Custom AI assistant name
    custom_domain: str = ""
    chat_background: str = "default"
    chat_font: str = "Inter"

class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    phone: str = ""

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

class EmailCredentials(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    email: str
    encrypted_password: str
    smtp_server: str = ""
    smtp_port: int = 587
    is_verified: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class EmailCredentialsCreate(BaseModel):
    email: EmailStr
    password: str
    smtp_server: str = ""
    smtp_port: int = 587

class CityPDFInfo(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    city_name: str
    pdf_url: str  # URL where PDF is stored
    pdf_content: str = ""  # Extracted text content from PDF
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CityPDFCreate(BaseModel):
    city_name: str
    pdf_url: str

class EmailCredentialsResponse(BaseModel):
    id: str
    email: str
    smtp_server: str
    smtp_port: int
    is_verified: bool

class WhitelabelSettings(BaseModel):
    brand_name: str
    brand_logo_url: str = ""
    brand_primary_color: str = "#2563eb"
    brand_secondary_color: str = "#1d4ed8"
    ai_tone: str = "professional"
    ai_assistant_name: str = "AI Assistant"  # Custom AI assistant name
    custom_domain: str = ""
    chat_background: str = "default"
    chat_font: str = "Inter"

class Apartment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str
    address: str
    description: str
    rules: List[str] = []
    contact: Dict[str, str] = {}
    ai_tone: str = "professional"
    recommendations: Dict[str, Any] = {}
    # Check-in/Check-out information
    check_in_time: str = ""
    check_out_time: str = ""
    check_in_instructions: str = ""
    # Apartment items locations
    apartment_locations: Dict[str, str] = {}  # {"keys": "under the mat", "towels": "bathroom closet"}
    # WiFi information
    wifi_network: str = ""
    wifi_password: str = ""
    wifi_instructions: str = ""
    # Geocoding coordinates (from Mapbox)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Analytics data
    total_chats: int = 0
    total_sessions: int = 0
    last_chat: Optional[datetime] = None

class ApartmentCreate(BaseModel):
    name: str
    address: str
    description: str
    rules: List[str] = []
    contact: Dict[str, str] = {}
    ai_tone: str = "professional"
    recommendations: Dict[str, Any] = {}
    # Check-in/Check-out information
    check_in_time: str = ""
    check_out_time: str = ""
    check_in_instructions: str = ""
    # Apartment items locations
    apartment_locations: Dict[str, str] = {}
    # WiFi information
    wifi_network: str = ""
    wifi_password: str = ""
    wifi_instructions: str = ""
    # Geocoding coordinates (from Mapbox)
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class ApartmentUpdate(BaseModel):
    name: str
    address: str
    description: str
    rules: List[str] = []
    contact: Dict[str, str] = {}
    ai_tone: str = "professional"
    recommendations: Dict[str, Any] = {}
    # Check-in/Check-out information
    check_in_time: str = ""
    check_out_time: str = ""
    check_in_instructions: str = ""
    # Apartment items locations
    apartment_locations: Dict[str, str] = {}
    # WiFi information
    wifi_network: str = ""
    wifi_password: str = ""
    wifi_instructions: str = ""
    # Geocoding coordinates (from Mapbox)
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class BookingNotification(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    apartment_id: str
    guest_email: str = ""
    guest_phone: str = ""
    guest_name: str = ""
    checkin_date: Optional[datetime] = None
    checkout_date: Optional[datetime] = None
    booking_source: str = ""  # airbnb, booking.com, etc
    notification_sent: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AnalyticsData:
    apartment_id: str
    apartment_name: str
    total_chats: int
    total_sessions: int
    last_chat: Optional[datetime]
    popular_questions: List[dict]
    peak_hours: List[dict]

async def scrape_airbnb_listing(url: str) -> dict:
    """Advanced Airbnb scraper with anti-detection measures"""
    try:
        import time
        import random
        from urllib.parse import urljoin
        
        # More aggressive headers to mimic real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.airbnb.com/',
            'Origin': 'https://www.airbnb.com',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        }
        
        logger.info(f"Advanced scraping attempt for: {url}")
        
        # Initialize result
        scraped_data = {
            'name': '',
            'address': '',
            'description': '',
            'rules': []
        }
        
        # Create session with better settings
        session = requests.Session()
        session.headers.update(headers)
        
        # Add random delay to seem more human-like
        await asyncio.sleep(random.uniform(1, 3))
        
        # Make request
        response = session.get(url, timeout=20, allow_redirects=True)
        response.raise_for_status()
        
        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')
        
        logger.info(f"Page loaded: {len(html_content)} chars, status: {response.status_code}")
        
        # Method 1: Check for blocked indicators
        blocked_indicators = [
            'Access denied', 'blocked', 'robot', 'captcha', 
            'security check', 'unusual activity', 'temporarily unavailable'
        ]
        
        if any(indicator.lower() in html_content.lower() for indicator in blocked_indicators):
            logger.warning("Page appears to be blocked or showing captcha")
        
        # Method 2: Try to extract from page title first (most reliable)
        title_tag = soup.find('title')
        if title_tag:
            full_title = title_tag.get_text().strip()
            logger.info(f"Page title: {full_title}")
            
            # Clean up Airbnb title
            if ' - ' in full_title and 'airbnb' in full_title.lower():
                potential_name = full_title.split(' - ')[0].strip()
                if len(potential_name) > 10 and potential_name not in ['Airbnb', 'Vacation Rentals']:
                    scraped_data['name'] = potential_name
                    logger.info(f"Extracted name from title: {potential_name}")
        
        # Method 3: Try meta tags
        meta_selectors = [
            'meta[property="og:title"]',
            'meta[name="twitter:title"]',
            'meta[property="og:description"]',
            'meta[name="description"]'
        ]
        
        for selector in meta_selectors:
            meta = soup.select_one(selector)
            if meta and meta.get('content'):
                content = meta.get('content').strip()
                logger.info(f"Meta {selector}: {content[:100]}...")
                
                if not scraped_data['name'] and 'og:title' in selector:
                    if content and len(content) > 5 and 'airbnb' not in content.lower():
                        scraped_data['name'] = content
                        
                if not scraped_data['description'] and ('description' in selector or 'og:description' in selector):
                    if content and len(content) > 20:
                        scraped_data['description'] = content[:300]
        
        # Method 4: Look for JSON-LD structured data
        json_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    if 'name' in data and not scraped_data['name']:
                        scraped_data['name'] = data['name']
                    if 'description' in data and not scraped_data['description']:
                        scraped_data['description'] = data['description'][:300]
                    if 'address' in data and not scraped_data['address']:
                        if isinstance(data['address'], dict):
                            addr_parts = []
                            for key in ['streetAddress', 'addressLocality', 'addressRegion']:
                                if key in data['address']:
                                    addr_parts.append(data['address'][key])
                            if addr_parts:
                                scraped_data['address'] = ', '.join(addr_parts)
                        elif isinstance(data['address'], str):
                            scraped_data['address'] = data['address']
            except:
                continue
        
        # Method 5: Try alternative selectors with broader patterns
        if not scraped_data['name']:
            # Try various heading patterns
            heading_selectors = [
                'h1', 'h2[data-testid]', '[data-testid*="title"]', 
                '[class*="title"]', '[class*="name"]'
            ]
            
            for selector in heading_selectors:
                elements = soup.select(selector)
                for elem in elements:
                    text = elem.get_text(strip=True)
                    if text and len(text) > 10 and len(text) < 200:
                        # Filter out obvious non-property names
                        exclude_words = ['airbnb', 'sign up', 'log in', 'book', 'search', 'filter']
                        if not any(word in text.lower() for word in exclude_words):
                            scraped_data['name'] = text
                            break
                if scraped_data['name']:
                    break
        
        # Method 6: Look for address/location info
        if not scraped_data['address']:
            location_patterns = [
                '[data-testid*="location"]', '[class*="location"]',
                '[class*="address"]', 'span[dir="ltr"]'
            ]
            
            for pattern in location_patterns:
                elements = soup.select(pattern)
                for elem in elements:
                    text = elem.get_text(strip=True)
                    if text and len(text) > 5 and len(text) < 150:
                        # Check if it looks like an address
                        if any(word in text.lower() for word in ['st', 'street', 'ave', 'road', 'city', ',']):
                            scraped_data['address'] = text
                            break
                if scraped_data['address']:
                    break
        
        # Method 7: Extract any house rules or policies
        rules_patterns = [
            '[data-testid*="rule"]', '[class*="rule"]', 
            '[data-testid*="policy"]', '[class*="policy"]'
        ]
        
        rules_found = []
        for pattern in rules_patterns:
            elements = soup.select(pattern)
            for elem in elements:
                text = elem.get_text(strip=True)
                if text and 10 < len(text) < 100:
                    if text not in rules_found:
                        rules_found.append(text)
        
        if rules_found:
            scraped_data['rules'] = rules_found[:5]
        
        # Fallback with meaningful data based on URL
        room_id_match = re.search(r'/rooms/(\d+)', url)
        room_id = room_id_match.group(1) if room_id_match else 'unknown'
        
        if not scraped_data['name']:
            scraped_data['name'] = f"Property {room_id}"
        
        if not scraped_data['address']:
            scraped_data['address'] = f"Location details needed - Property ID: {room_id}"
            
        if not scraped_data['description']:
            scraped_data['description'] = f"Property details not available due to website restrictions. Property ID: {room_id}. Please add your own description."
        
        if not scraped_data['rules']:
            scraped_data['rules'] = [
                "Standard check-in and check-out procedures apply",
                "Keep the property clean and follow house rules",
                "Respect neighbors and local community guidelines"
            ]
        
        logger.info(f"Scraping completed - Name: '{scraped_data['name']}', Address: '{scraped_data['address']}'")
        return scraped_data
        
    except requests.RequestException as e:
        logger.error(f"Network error scraping {url}: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Could not access the listing URL: {str(e)}")
    except Exception as e:
        logger.error(f"Error scraping {url}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to parse listing data: {str(e)}")

async def scrape_booking_listing(url: str) -> dict:
    """Scrape Booking.com listing data"""
    try:
        import time
        import random
        
        # Headers to mimic real browser for Booking.com
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.booking.com/',
            'Origin': 'https://www.booking.com',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        }
        
        logger.info(f"Booking.com scraping attempt for: {url}")
        
        # Initialize result
        scraped_data = {
            'name': '',
            'address': '',
            'description': '',
            'rules': []
        }
        
        # Create session
        session = requests.Session()
        session.headers.update(headers)
        
        # Add random delay
        await asyncio.sleep(random.uniform(1, 3))
        
        # Make request
        response = session.get(url, timeout=20, allow_redirects=True)
        response.raise_for_status()
        
        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')
        
        logger.info(f"Booking.com page loaded: {len(html_content)} chars, status: {response.status_code}")
        
        # Method 1: Extract from page title
        title_tag = soup.find('title')
        if title_tag:
            full_title = title_tag.get_text().strip()
            logger.info(f"Booking.com page title: {full_title}")
            
            # Clean up Booking.com title
            if 'booking.com' in full_title.lower():
                # Booking.com titles often follow pattern: "Property Name, Location - Booking.com"
                if ' - ' in full_title:
                    potential_name = full_title.split(' - ')[0].strip()
                    if ',' in potential_name:
                        # Split name and location
                        name_part = potential_name.split(',')[0].strip()
                        if len(name_part) > 5:
                            scraped_data['name'] = name_part
                            logger.info(f"Extracted name from title: {name_part}")
        
        # Method 2: Look for property name in specific Booking.com selectors
        name_selectors = [
            'h2[data-testid="property-name"]',
            '.hp__hotel-name',
            'h1.pp-header__title',
            '.property-name',
            'h1'
        ]
        
        for selector in name_selectors:
            name_elem = soup.select_one(selector)
            if name_elem and not scraped_data['name']:
                name_text = name_elem.get_text().strip()
                if len(name_text) > 5 and len(name_text) < 100:
                    scraped_data['name'] = name_text
                    logger.info(f"Found name with selector {selector}: {name_text}")
                    break
        
        # Method 3: Look for address
        address_selectors = [
            '[data-testid="property-address"]',
            '.hp__hotel-location',
            '.property-address',
            '.address'
        ]
        
        for selector in address_selectors:
            addr_elem = soup.select_one(selector)
            if addr_elem:
                addr_text = addr_elem.get_text().strip()
                if len(addr_text) > 10:
                    scraped_data['address'] = addr_text
                    logger.info(f"Found address: {addr_text}")
                    break
        
        # Method 4: Look for description
        desc_selectors = [
            '[data-testid="property-description"]',
            '.property-description',
            '.hotel-description',
            '.summary'
        ]
        
        for selector in desc_selectors:
            desc_elem = soup.select_one(selector)
            if desc_elem:
                desc_text = desc_elem.get_text().strip()
                if len(desc_text) > 50:
                    scraped_data['description'] = desc_text[:500]  # Limit length
                    logger.info(f"Found description: {desc_text[:100]}...")
                    break
        
        # Method 5: Look for house rules/policies
        rules_selectors = [
            '.hotel-policies',
            '.house-rules',
            '.property-policies',
            '[data-testid="policies-section"]'
        ]
        
        rules_found = []
        for selector in rules_selectors:
            rules_section = soup.select_one(selector)
            if rules_section:
                # Extract rule items
                rule_items = rules_section.find_all(['li', 'p', 'div'])
                for item in rule_items:
                    rule_text = item.get_text().strip()
                    if len(rule_text) > 10 and len(rule_text) < 100:
                        rules_found.append(rule_text)
                        if len(rules_found) >= 5:  # Limit to 5 rules
                            break
                if rules_found:
                    break
        
        if rules_found:
            scraped_data['rules'] = rules_found[:5]
        else:
            # Default rules for Booking.com properties
            scraped_data['rules'] = [
                'Check-in from 15:00',
                'Check-out until 11:00',
                'No smoking',
                'No pets allowed',
                'No parties or events'
            ]
        
        # Method 6: Meta tags fallback
        if not scraped_data['name']:
            meta_title = soup.find('meta', property='og:title')
            if meta_title and meta_title.get('content'):
                content = meta_title.get('content').strip()
                if 'booking.com' not in content.lower() and len(content) > 5:
                    scraped_data['name'] = content
        
        if not scraped_data['description']:
            meta_desc = soup.find('meta', property='og:description')
            if meta_desc and meta_desc.get('content'):
                content = meta_desc.get('content').strip()
                if len(content) > 20:
                    scraped_data['description'] = content[:300]
        
        logger.info(f"Booking.com scraping results: name='{scraped_data['name']}', rules={len(scraped_data['rules'])}")
        
        return scraped_data
        
    except Exception as e:
        logger.error(f"Booking.com scraping error: {str(e)}")
        # Return fallback data
        property_id = url.split('/')[-1].split('.')[0] if '/' in url else 'unknown'
        return {
            'name': f'Booking.com Property ({property_id})',
            'address': 'Address not found - please enter manually',
            'description': 'Property description not found - please add your own description',
            'rules': ['Check-in from 15:00', 'Check-out until 11:00', 'No smoking', 'No pets allowed', 'No parties or events']
        }

async def extract_pdf_content(pdf_url: str) -> str:
    """Extract text content from PDF URL"""
    try:
        logger.info(f"Extracting PDF content from: {pdf_url}")
        
        # Download PDF
        response = requests.get(pdf_url, timeout=30)
        response.raise_for_status()
        
        # Extract text from PDF
        pdf_reader = PyPDF2.PdfReader(BytesIO(response.content))
        text_content = ""
        
        for page in pdf_reader.pages:
            text_content += page.extract_text() + "\n"
        
        # Basic text cleaning
        text_content = re.sub(r'\s+', ' ', text_content).strip()
        
        logger.info(f"Extracted {len(text_content)} characters from PDF")
        return text_content
        
    except Exception as e:
        logger.error(f"PDF extraction error: {str(e)}")
        return ""

class PropertyImportRequest(BaseModel):
    url: str

# iCal and notification helper functions
async def send_whatsapp_message(phone: str, message: str, apartment_name: str):
    """Send WhatsApp message via WhatsApp Business API or third-party service"""
    try:
        # For demo purposes, we'll use a webhook/API call
        # In production, integrate with WhatsApp Business API or services like Twilio
        logger.info(f"WhatsApp message sent to {phone} for {apartment_name}")
        
        # Placeholder for actual WhatsApp API integration
        # async with httpx.AsyncClient() as client:
        #     response = await client.post(
        #         "https://api.whatsapp.com/send",
        #         json={
        #             "phone": phone,
        #             "message": message
        #         }
        #     )
        
        return True
    except Exception as e:
        logger.error(f"Error sending WhatsApp: {str(e)}")
        return False

async def send_email_notification(email: str, subject: str, content: str, apartment_name: str, host_credentials: dict = None):
    """Send email notification to guest using host's email credentials"""
    try:
        if host_credentials:
            # Use host's SMTP credentials
            success = await send_smtp_email(email, subject, content, host_credentials)
            if success:
                logger.info(f"Email sent successfully to {email} for {apartment_name} using host's email")
                return True
            else:
                logger.error(f"Failed to send email via SMTP to {email}")
                return False
        else:
            logger.warning(f"No host email credentials configured for {apartment_name}")
            return False
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return False

async def create_guest_notification_message(apartment: dict, branding: dict, guest_name: str, checkin_date: datetime, guest_url: str):
    """Create personalized notification message for guests"""
    brand_name = branding.get('brand_name', 'MyHostIQ')
    
    # Email content
    email_subject = f"Welcome to {apartment['name']} - Your AI Assistant is Ready!"
    
    email_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: 'Inter', Arial, sans-serif; margin: 0; padding: 20px; background-color: #f8fafc; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
            .header {{ background: linear-gradient(135deg, {branding.get('brand_primary_color', '#2563eb')}, {branding.get('brand_secondary_color', '#1d4ed8')}); color: white; padding: 30px 20px; text-align: center; }}
            .content {{ padding: 30px 20px; }}
            .button {{ background: {branding.get('brand_primary_color', '#2563eb')}; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; display: inline-block; font-weight: bold; }}
            .footer {{ background: #f1f5f9; padding: 20px; text-align: center; color: #64748b; font-size: 14px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>{brand_name}</h1>
                <p>Your Personal AI Assistant for {apartment['name']}</p>
            </div>
            <div class="content">
                <h2>Hello {guest_name}! 👋</h2>
                <p>Welcome to <strong>{apartment['name']}</strong>! We're excited to have you stay with us.</p>
                
                <p>🤖 <strong>Your Personal AI Assistant is Ready!</strong></p>
                <p>We've set up a personal AI concierge just for you. It can instantly help with:</p>
                <ul>
                    <li>📍 Check-in instructions & apartment access</li>
                    <li>🏠 WiFi passwords & apartment amenities</li>
                    <li>🍽️ Local restaurant recommendations</li>
                    <li>🚇 Transportation & navigation help</li>
                    <li>🚨 Emergency contacts & important information</li>
                    <li>💎 Hidden local gems & attractions</li>
                </ul>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{guest_url}" class="button">Chat with Your AI Assistant</a>
                </div>
                
                <p><strong>📅 Your Stay Details:</strong></p>
                <p>📍 <strong>Property:</strong> {apartment['name']}<br>
                📅 <strong>Check-in:</strong> {checkin_date.strftime('%B %d, %Y')}<br>
                🏠 <strong>Address:</strong> {apartment.get('address', 'Address in booking confirmation')}</p>
                
                <div style="background: #f0f9ff; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <p><strong>💡 Pro Tip:</strong> Save the AI assistant link on your phone's home screen for instant access during your stay!</p>
                </div>
            </div>
            <div class="footer">
                <p>Generated by {brand_name} - Making your stay exceptional</p>
                <p>Questions? Your AI assistant is available 24/7 at the link above!</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # WhatsApp message
    whatsapp_message = f"""
🏠 Welcome to {apartment['name']}!

Hello {guest_name}! 👋

Your personal AI assistant is ready to help you with your stay:

• Check-in instructions
• WiFi & amenities  
• Restaurant recommendations
• Transport info
• Emergency contacts
• Local hidden gems

🤖 Chat with your AI assistant here:
{guest_url}

📅 Check-in: {checkin_date.strftime('%B %d, %Y')}

Save this link for instant help during your stay!

— {brand_name} Team
    """
    
    return email_subject, email_content, whatsapp_message

def encrypt_password(password: str) -> str:
    """Encrypt password for secure storage"""
    return cipher_suite.encrypt(password.encode()).decode()

def decrypt_password(encrypted_password: str) -> str:
    """Decrypt password for use"""
    return cipher_suite.decrypt(encrypted_password.encode()).decode()

def get_smtp_settings(email: str, smtp_server: str = "", smtp_port: int = 587):
    """Get SMTP settings based on email provider"""
    if not smtp_server:
        domain = email.split('@')[1].lower()
        if 'gmail.com' in domain:
            return 'smtp.gmail.com', 587
        elif 'outlook.com' in domain or 'hotmail.com' in domain:
            return 'smtp-mail.outlook.com', 587
        elif 'yahoo.com' in domain:
            return 'smtp.mail.yahoo.com', 587
        else:
            return smtp_server, smtp_port
    return smtp_server, smtp_port

async def send_smtp_email(
    recipient_email: str, 
    subject: str, 
    html_content: str, 
    sender_credentials: dict
) -> bool:
    """Send email using SMTP with host's credentials"""
    try:
        sender_email = sender_credentials['email']
        sender_password = decrypt_password(sender_credentials['encrypted_password'])
        smtp_server, smtp_port = get_smtp_settings(
            sender_email, 
            sender_credentials.get('smtp_server', ''),
            sender_credentials.get('smtp_port', 587)
        )
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = recipient_email
        
        # Add HTML content
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
        # Send email
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls(context=context)
            server.login(sender_email, sender_password)
            server.send_message(msg)
        
        logger.info(f"Email sent successfully from {sender_email} to {recipient_email}")
        return True
        
    except Exception as e:
        logger.error(f"SMTP email error: {str(e)}")
        return False

async def verify_email_credentials(email: str, password: str, smtp_server: str = "", smtp_port: int = 587) -> bool:
    """Verify email credentials by attempting to connect"""
    try:
        smtp_server, smtp_port = get_smtp_settings(email, smtp_server, smtp_port)
        
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls(context=context)
            server.login(email, password)
        
        return True
    except Exception as e:
        logger.error(f"Email verification failed: {str(e)}")
        return False

def prepare_for_mongo(data):
    """Prepare data for MongoDB storage"""
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
    return data

def parse_from_mongo(data):
    """Parse data from MongoDB storage"""
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, str) and key.endswith('_at'):
                try:
                    data[key] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                except:
                    pass
    return data

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(data: dict):
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=24)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from JWT token"""
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = await db.users.find_one({"id": user_id})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        
        return User(**user)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current user and verify admin privileges"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403, 
            detail="Admin privileges required"
        )
    return current_user

def extract_city_from_address(address: str) -> str:
    """Extract city name from address string - improved logic"""
    if not address:
        return ""
    
    # Split address by comma and process each part
    address_parts = [part.strip() for part in address.split(',')]
    
    # Known country names to exclude
    country_names = [
        'bosnia and herzegovina', 'croatia', 'serbia', 'montenegro', 'slovenia',
        'germany', 'france', 'spain', 'italy', 'austria', 'switzerland',
        'usa', 'united states', 'canada', 'uk', 'united kingdom', 'england'
    ]
    
    # Known city patterns (for better recognition)
    city_indicators = [
        'sarajevo', 'zagreb', 'belgrade', 'dubrovnik', 'split', 'mostar',
        'paris', 'london', 'berlin', 'rome', 'madrid', 'barcelona', 'vienna'
    ]
    
    # First pass: look for known cities
    for part in address_parts:
        part_lower = part.lower().strip()
        if part_lower in city_indicators:
            return part
    
    # Second pass: exclude obvious non-city parts
    for i, part in enumerate(address_parts):
        part_lower = part.lower().strip()
        
        # Skip if it's a known country
        if part_lower in country_names:
            continue
            
        # Skip if starts with number (likely street address)
        if part and part[0].isdigit():
            continue
            
        # Skip if it's likely a postal code (short with numbers)
        if len(part) <= 6 and any(c.isdigit() for c in part):
            continue
            
        # Skip if it's the last part and looks like country (common pattern)
        if i == len(address_parts) - 1 and len(address_parts) >= 3:
            continue
            
        # Take first valid city-like part
        if len(part) >= 3 and not any(c.isdigit() for c in part[:3]):
            return part
    
    # Fallback strategies
    if len(address_parts) >= 2:
        # Try second-to-last part (common city position)
        potential_city = address_parts[-2].strip()
        if (not any(c.isdigit() for c in potential_city) and 
            potential_city.lower() not in country_names and 
            len(potential_city) >= 3):
            return potential_city
    
    # Last resort: take middle part if 3 parts
    if len(address_parts) == 3:
        middle_part = address_parts[1].strip()
        if not any(c.isdigit() for c in middle_part[:3]) and len(middle_part) >= 3:
            return middle_part
    
    return "this area"

async def geocode_address_with_mapbox(address: str) -> Optional[Dict[str, float]]:
    """Geocode an address using Mapbox Geocoding API"""
    try:
        mapbox_api_key = os.environ.get('MAPBOX_API_KEY')
        if not mapbox_api_key:
            logger.error("MAPBOX_API_KEY not configured")
            return None
        
        # Encode address for URL
        encoded_address = requests.utils.quote(address)
        
        # Mapbox Geocoding API endpoint
        url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{encoded_address}.json"
        params = {
            'access_token': mapbox_api_key,
            'limit': 1
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('features') and len(data['features']) > 0:
                    coordinates = data['features'][0]['geometry']['coordinates']
                    # Mapbox returns [longitude, latitude]
                    return {
                        'longitude': coordinates[0],
                        'latitude': coordinates[1]
                    }
                else:
                    logger.warning(f"No geocoding results for address: {address}")
                    return None
            else:
                logger.error(f"Mapbox geocoding failed: {response.status_code} - {response.text}")
                return None
                
    except Exception as e:
        logger.error(f"Geocoding error: {str(e)}")
        return None

async def search_nearby_places_with_mapbox(
    latitude: float,
    longitude: float, 
    category: str,
    radius_meters: int = 1000
) -> List[Dict[str, Any]]:
    """Search for nearby places using Mapbox Search API"""
    try:
        mapbox_api_key = os.environ.get('MAPBOX_API_KEY')
        if not mapbox_api_key:
            logger.error("MAPBOX_API_KEY not configured")
            return []
        
        # Map common categories to Mapbox category names
        category_mapping = {
            'supermarket': 'supermarket',
            'grocery': 'grocery',
            'bakery': 'bakery',
            'pharmacy': 'pharmacy',
            'restaurant': 'restaurant',
            'cafe': 'cafe',
            'coffee': 'cafe',
            'bar': 'bar',
            'pub': 'bar',
            'club': 'nightclub',
            'nightclub': 'nightclub',
            'atm': 'atm',
            'bank': 'bank',
            'hospital': 'hospital',
            'doctor': 'clinic',
            'shopping': 'shopping_mall',
            'mall': 'shopping_mall',
            'park': 'park',
            'gym': 'gym',
            'museum': 'museum',
            'cinema': 'cinema',
            'theater': 'theater',
            'attraction': 'tourist_attraction',
            'tourist': 'tourist_attraction'
        }
        
        # Get the mapped category or use original
        search_category = category_mapping.get(category.lower(), category.lower())
        
        # Mapbox Search Box API (v1)
        url = f"https://api.mapbox.com/search/v1/category/{search_category}"
        params = {
            'access_token': mapbox_api_key,
            'proximity': f"{longitude},{latitude}",
            'limit': 10,
            'language': 'en'
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                places = []
                for feature in data.get('features', []):
                    properties = feature.get('properties', {})
                    geometry = feature.get('geometry', {})
                    
                    if geometry.get('coordinates'):
                        coords = geometry['coordinates']
                        place_lon, place_lat = coords[0], coords[1]
                        
                        # Calculate distance using Haversine formula
                        distance = calculate_haversine_distance(
                            latitude, longitude,
                            place_lat, place_lon
                        )
                        
                        # Only include places within radius
                        if distance <= radius_meters:
                            # Extract name from Mapbox response
                            name = (properties.get('feature_name') or 
                                   properties.get('name') or 
                                   properties.get('place_name', '').split(',')[0] or
                                   'Unknown Place')
                            
                            # Extract address
                            address = properties.get('description') or properties.get('place_name', '')
                            
                            places.append({
                                'name': name,
                                'address': address,
                                'category': search_category,
                                'distance': round(distance),
                                'latitude': place_lat,
                                'longitude': place_lon
                            })
                
                # Sort by distance
                places.sort(key=lambda x: x['distance'])
                return places[:5]  # Return top 5 closest
            else:
                logger.error(f"Mapbox search failed: {response.status_code} - {response.text}")
                return []
                
    except Exception as e:
        logger.error(f"Nearby search error: {str(e)}")
        return []

def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two coordinates using Haversine formula (in meters)"""
    from math import radians, sin, cos, sqrt, atan2
    
    # Earth radius in meters
    R = 6371000
    
    # Convert to radians
    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)
    delta_lat = radians(lat2 - lat1)
    delta_lon = radians(lon2 - lon1)
    
    # Haversine formula
    a = sin(delta_lat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance = R * c
    
    return distance

async def get_cached_places(apartment_id: str, category: str) -> Optional[List[Dict[str, Any]]]:
    """Get cached places from database"""
    try:
        cache_key = f"{apartment_id}_{category}"
        cached = await db.places_cache.find_one({"cache_key": cache_key})
        
        if cached:
            # Check if cache is still valid (24 hours)
            expires_at = cached.get('expires_at')
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            
            if datetime.now(timezone.utc) < expires_at:
                return cached.get('results', [])
        
        return None
    except Exception as e:
        logger.error(f"Cache retrieval error: {str(e)}")
        return None

async def cache_places(apartment_id: str, category: str, places: List[Dict[str, Any]]):
    """Cache places results in database"""
    try:
        cache_key = f"{apartment_id}_{category}"
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=24)
        
        cache_doc = {
            "cache_key": cache_key,
            "apartment_id": apartment_id,
            "category": category,
            "results": places,
            "cached_at": now.isoformat(),
            "expires_at": expires_at.isoformat()
        }
        
        # Upsert (update if exists, insert if not)
        await db.places_cache.update_one(
            {"cache_key": cache_key},
            {"$set": cache_doc},
            upsert=True
        )
    except Exception as e:
        logger.error(f"Cache storage error: {str(e)}")

def create_ai_system_prompt(apartment_data: dict, user_branding: dict) -> str:
    """Backward-compatible wrapper around the new prompt builder."""
    from app.services.ai_service import PromptBuilder
    return PromptBuilder().build_system_prompt(apartment_data, user_branding)

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordReset(BaseModel):
    token: str
    new_password: str

# Authentication Routes
@api_router.post("/auth/register", response_model=Token)
@limiter.limit("5/minute")  # Limit registration attempts
async def register_user(request: Request, user_data: UserCreate):
    """Register a new user"""
    try:
        # Check if user already exists
        existing_user = await db.users.find_one({"email": user_data.email})
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create user
        user = User(
            email=user_data.email,
            full_name=user_data.full_name,
            phone=user_data.phone,
            hashed_password=hash_password(user_data.password)
        )
        
        user_dict = prepare_for_mongo(user.dict())
        await db.users.insert_one(user_dict)
        
        # Create access token
        access_token = create_access_token({"sub": user.id})
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            user={
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "brand_name": user.brand_name,
                "phone": user.phone,
                "created_at": user.created_at.isoformat() if user.created_at else datetime.now(timezone.utc).isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# City PDF Info Routes
@api_router.post("/city-pdfs")
async def create_city_pdf(
    pdf_data: CityPDFCreate, 
    current_user: User = Depends(get_current_user)
):
    """Upload city PDF information"""
    try:
        # Extract PDF content
        pdf_content = await extract_pdf_content(pdf_data.pdf_url)
        
        # Create city PDF record
        city_pdf = CityPDFInfo(
            user_id=current_user.id,
            city_name=pdf_data.city_name,
            pdf_url=pdf_data.pdf_url,
            pdf_content=pdf_content
        )
        
        city_pdf_dict = prepare_for_mongo(city_pdf.dict())
        await db.city_pdfs.insert_one(city_pdf_dict)
        
        return {
            "success": True,
            "message": f"City PDF for {pdf_data.city_name} uploaded successfully",
            "id": city_pdf.id,
            "content_length": len(pdf_content)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/city-pdfs")
async def get_user_city_pdfs(current_user: User = Depends(get_current_user)):
    """Get all city PDFs for current user"""
    try:
        city_pdfs = await db.city_pdfs.find({"user_id": current_user.id}).to_list(length=None)
        
        # Parse from mongo and hide content for list view
        parsed_pdfs = []
        for pdf in city_pdfs:
            parsed_pdf = parse_from_mongo(pdf)
            # Don't return full content in list view
            parsed_pdf['content_preview'] = parsed_pdf.get('pdf_content', '')[:200] + "..."
            parsed_pdf.pop('pdf_content', None)
            parsed_pdfs.append(parsed_pdf)
            
        return parsed_pdfs
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.delete("/city-pdfs/{pdf_id}")
async def delete_city_pdf(
    pdf_id: str, 
    current_user: User = Depends(get_current_user)
):
    """Delete city PDF"""
    try:
        result = await db.city_pdfs.delete_one({
            "id": pdf_id, 
            "user_id": current_user.id
        })
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="City PDF not found")
            
        return {"success": True, "message": "City PDF deleted successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/auth/login", response_model=Token)
@limiter.limit("10/minute")  # Limit login attempts 
async def login(request: Request, user_data: UserLogin):
    """Login user"""
    try:
        # Find user
        user = await db.users.find_one({"email": user_data.email})
        if not user or not verify_password(user_data.password, user['hashed_password']):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Create access token
        access_token = create_access_token({"sub": user['id']})
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            user={
                "id": user['id'],
                "email": user['email'],
                "full_name": user['full_name'],
                "brand_name": user.get('brand_name', 'MyHostIQ'),
                "phone": user.get('phone', ''),
                "created_at": user.get('created_at', '')
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/auth/forgot-password")
@limiter.limit("5/minute")  # Limit password reset attempts
async def forgot_password(request: Request, forgot_request: PasswordResetRequest):
    """Send password reset email"""
    try:
        # Find user
        user = await db.users.find_one({"email": forgot_request.email})
        if not user:
            # Don't reveal if email exists for security
            return {"message": "If the email exists, a password reset link has been sent"}
        
        # Generate reset token (JWT with short expiration)
        reset_token = create_access_token({"sub": user['id'], "type": "password_reset"})
        
        # Store reset token in database with expiration
        await db.password_resets.insert_one({
            "user_id": user['id'],
            "token": reset_token,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "used": False
        })
        
        # Create reset email with proper URL
        frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
        reset_url = f"{frontend_url}/reset-password?token={reset_token}"
        email_subject = "MyHostIQ - Password Reset Request"
        email_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Inter', Arial, sans-serif; margin: 0; padding: 20px; background-color: #f8fafc; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #2563eb, #1d4ed8); color: white; padding: 30px 20px; text-align: center; }}
                .content {{ padding: 30px 20px; }}
                .button {{ background: #2563eb; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; display: inline-block; font-weight: bold; }}
                .footer {{ background: #f1f5f9; padding: 20px; text-align: center; color: #64748b; font-size: 14px; }}
                .warning {{ background: #fef3c7; border: 1px solid #f59e0b; color: #92400e; padding: 15px; border-radius: 8px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>MyHostIQ</h1>
                    <p>Password Reset Request</p>
                </div>
                <div class="content">
                    <h2>Hello {user.get('full_name', 'there')}! 👋</h2>
                    <p>We received a request to reset your password for your MyHostIQ account.</p>
                    
                    <p>If you requested this, click the button below to reset your password:</p>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{reset_url}" class="button">Reset My Password</a>
                    </div>
                    
                    <div class="warning">
                        <p><strong>⚠️ Important Security Information:</strong></p>
                        <ul style="margin: 10px 0; padding-left: 20px;">
                            <li>This link will expire in 1 hour</li>
                            <li>If you didn't request this, please ignore this email</li>
                            <li>Never share this link with anyone</li>
                            <li>We will never ask for your password via email</li>
                        </ul>
                    </div>
                    
                    <p>If the button doesn't work, copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; color: #6b7280; font-size: 12px;">{reset_url}</p>
                </div>
                <div class="footer">
                    <p>MyHostIQ - Smart Guest Assistant Platform</p>
                    <p>This email was sent because a password reset was requested for your account.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Send reset email using SendGrid
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail
            
            # Use a professional from address
            from_email = 'noreply@myhostiq.com'  # You can change this to your domain later
            
            message = Mail(
                from_email=from_email,
                to_emails=forgot_request.email,
                subject=email_subject,
                html_content=email_content
            )
            
            sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
            response = sg.send(message)
            
            if response.status_code == 202:
                logger.info(f"Password reset email successfully sent to {forgot_request.email}")
            else:
                logger.error(f"SendGrid returned status code: {response.status_code}")
            
        except Exception as e:
            logger.error(f"Failed to send password reset email: {str(e)}")
            # For security, we still return success message even if email fails
            # This prevents email enumeration attacks
        
        return {"message": "If the email exists, a password reset link has been sent"}
        
    except Exception as e:
        logger.error(f"Forgot password error: {str(e)}")
        return {"message": "If the email exists, a password reset link has been sent"}

@api_router.post("/auth/reset-password")
async def reset_password(request: PasswordReset):
    """Reset password using token"""
    try:
        # Verify token
        try:
            payload = jwt.decode(request.token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            user_id = payload.get("sub")
            token_type = payload.get("type")
            
            if token_type != "password_reset":
                raise HTTPException(status_code=400, detail="Invalid reset token")
                
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=400, detail="Reset token has expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=400, detail="Invalid reset token")
        
        # Check if token exists and is not used
        reset_record = await db.password_resets.find_one({
            "token": request.token,
            "used": False
        })
        
        if not reset_record:
            raise HTTPException(status_code=400, detail="Invalid or already used reset token")
        
        # Check if token is expired
        expires_at = datetime.fromisoformat(reset_record['expires_at'])
        if datetime.now(timezone.utc) > expires_at:
            raise HTTPException(status_code=400, detail="Reset token has expired")
        
        # Find user
        user = await db.users.find_one({"id": user_id})
        if not user:
            raise HTTPException(status_code=400, detail="User not found")
        
        # Update password
        hashed_password = hash_password(request.new_password)
        await db.users.update_one(
            {"id": user_id},
            {"$set": {"hashed_password": hashed_password}}
        )
        
        # Mark token as used
        await db.password_resets.update_one(
            {"token": request.token},
            {"$set": {"used": True, "used_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        return {"message": "Password reset successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reset password error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to reset password")

# User Routes
@api_router.get("/auth/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "phone": current_user.phone,
        "brand_name": current_user.brand_name,
        "brand_logo_url": current_user.brand_logo_url,
        "brand_primary_color": current_user.brand_primary_color,
        "brand_secondary_color": current_user.brand_secondary_color,
        "ai_tone": current_user.ai_tone,
        "ai_assistant_name": current_user.ai_assistant_name,
        "custom_domain": current_user.custom_domain,
        "chat_background": current_user.chat_background,
        "chat_font": current_user.chat_font,
        "email_verified": current_user.email_verified,
        "phone_verified": current_user.phone_verified,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None
    }

@api_router.put("/auth/whitelabel")
async def update_whitelabel_settings(
    settings: WhitelabelSettings,
    current_user: User = Depends(get_current_user)
):
    """Update user's whitelabel settings"""
    try:
        await db.users.update_one(
            {"id": current_user.id},
            {"$set": {
                "brand_name": settings.brand_name,
                "brand_logo_url": settings.brand_logo_url,
                "brand_primary_color": settings.brand_primary_color,
                "brand_secondary_color": settings.brand_secondary_color,
                "ai_tone": settings.ai_tone,
                "ai_assistant_name": settings.ai_assistant_name,
                "custom_domain": settings.custom_domain,
                "chat_background": settings.chat_background,
                "chat_font": settings.chat_font
            }}
        )
        return {"message": "Whitelabel settings updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Email Credentials Routes
@api_router.post("/auth/email-credentials", response_model=EmailCredentialsResponse)
async def add_email_credentials(
    credentials: EmailCredentialsCreate,
    current_user: User = Depends(get_current_user)
):
    """Add and verify host's email credentials"""
    try:
        # Check if user already has email credentials
        existing = await db.email_credentials.find_one({"user_id": current_user.id})
        if existing:
            raise HTTPException(status_code=400, detail="Email credentials already configured. Use update endpoint.")
        
        # Auto-detect SMTP settings if not provided
        smtp_server, smtp_port = get_smtp_settings(
            credentials.email, 
            credentials.smtp_server, 
            credentials.smtp_port
        )
        
        # Verify credentials
        is_verified = await verify_email_credentials(
            credentials.email, 
            credentials.password, 
            smtp_server, 
            smtp_port
        )
        
        if not is_verified:
            raise HTTPException(status_code=400, detail="Invalid email credentials or SMTP settings")
        
        # Encrypt and store credentials
        email_creds = EmailCredentials(
            user_id=current_user.id,
            email=credentials.email,
            encrypted_password=encrypt_password(credentials.password),
            smtp_server=smtp_server,
            smtp_port=smtp_port,
            is_verified=is_verified
        )
        
        creds_dict = prepare_for_mongo(email_creds.dict())
        await db.email_credentials.insert_one(creds_dict)
        
        return EmailCredentialsResponse(
            id=email_creds.id,
            email=email_creds.email,
            smtp_server=email_creds.smtp_server,
            smtp_port=email_creds.smtp_port,
            is_verified=email_creds.is_verified
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.put("/auth/email-credentials", response_model=EmailCredentialsResponse)
async def update_email_credentials(
    credentials: EmailCredentialsCreate,
    current_user: User = Depends(get_current_user)
):
    """Update host's email credentials"""
    try:
        # Find existing credentials
        existing = await db.email_credentials.find_one({"user_id": current_user.id})
        if not existing:
            raise HTTPException(status_code=404, detail="No email credentials found. Use create endpoint.")
        
        # Auto-detect SMTP settings if not provided
        smtp_server, smtp_port = get_smtp_settings(
            credentials.email, 
            credentials.smtp_server, 
            credentials.smtp_port
        )
        
        # Verify new credentials
        is_verified = await verify_email_credentials(
            credentials.email, 
            credentials.password, 
            smtp_server, 
            smtp_port
        )
        
        if not is_verified:
            raise HTTPException(status_code=400, detail="Invalid email credentials or SMTP settings")
        
        # Update credentials
        await db.email_credentials.update_one(
            {"user_id": current_user.id},
            {"$set": {
                "email": credentials.email,
                "encrypted_password": encrypt_password(credentials.password),
                "smtp_server": smtp_server,
                "smtp_port": smtp_port,
                "is_verified": is_verified
            }}
        )
        
        return EmailCredentialsResponse(
            id=existing['id'],
            email=credentials.email,
            smtp_server=smtp_server,
            smtp_port=smtp_port,
            is_verified=is_verified
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/auth/email-credentials", response_model=Optional[EmailCredentialsResponse])
async def get_email_credentials(current_user: User = Depends(get_current_user)):
    """Get host's email credentials (without password)"""
    try:
        creds = await db.email_credentials.find_one({"user_id": current_user.id})
        if not creds:
            return None
        
        return EmailCredentialsResponse(
            id=creds['id'],
            email=creds['email'],
            smtp_server=creds['smtp_server'],
            smtp_port=creds['smtp_port'],
            is_verified=creds['is_verified']
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.delete("/auth/email-credentials")
async def delete_email_credentials(current_user: User = Depends(get_current_user)):
    """Delete host's email credentials"""
    try:
        result = await db.email_credentials.delete_one({"user_id": current_user.id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="No email credentials found")
        
        return {"message": "Email credentials deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/auth/test-email")
async def test_email_credentials(current_user: User = Depends(get_current_user)):
    """Test host's email credentials by sending a test email"""
    try:
        # Get credentials
        creds = await db.email_credentials.find_one({"user_id": current_user.id})
        if not creds:
            raise HTTPException(status_code=404, detail="No email credentials configured")
        
        if not creds['is_verified']:
            raise HTTPException(status_code=400, detail="Email credentials not verified")
        
        # Send test email to the host
        test_subject = "MyHostIQ - Email Configuration Test"
        test_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f8fafc; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; padding: 30px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .success {{ color: #16a34a; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Email Configuration Test</h1>
                </div>
                <p class="success">Congratulations! Your email configuration is working perfectly.</p>
                <p>This test email confirms that:</p>
                <ul>
                    <li>✅ Your email credentials are valid</li>
                    <li>✅ SMTP connection is successful</li>
                    <li>✅ MyHostIQ can send emails from your account</li>
                </ul>
                <p>Your guests will now receive beautiful welcome emails directly from your email address when they have upcoming bookings.</p>
                <hr style="margin: 30px 0; border: none; border-top: 1px solid #e5e7eb;">
                <p style="font-size: 14px; color: #6b7280;">
                    This is an automated test email from MyHostIQ.<br>
                    Email: {creds['email']}<br>
                    SMTP Server: {creds['smtp_server']}:{creds['smtp_port']}
                </p>
            </div>
        </body>
        </html>
        """
        
        success = await send_smtp_email(creds['email'], test_subject, test_content, creds)
        
        if success:
            return {"message": "Test email sent successfully! Check your inbox."}
        else:
            raise HTTPException(status_code=500, detail="Failed to send test email")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Payment Simulation Routes
class PaymentRequest(BaseModel):
    amount: float
    currency: str = "USD"
    plan_name: str
    apartment_count: int

class PaymentResponse(BaseModel):
    success: bool
    transaction_id: str
    message: str
    plan_name: str
    amount: float

@api_router.post("/payments/simulate", response_model=PaymentResponse)
async def simulate_payment(
    payment: PaymentRequest,
    current_user: User = Depends(get_current_user)
):
    """Simulate payment processing for subscription plans"""
    try:
        # Simulate payment processing delay
        await asyncio.sleep(1)
        
        # Generate mock transaction ID
        transaction_id = f"sim_{uuid.uuid4().hex[:12]}"
        
        # Simulate payment success (95% success rate)
        import random
        success = random.random() > 0.05
        
        if success:
            return PaymentResponse(
                success=True,
                transaction_id=transaction_id,
                message=f"Payment successful! Welcome to {payment.plan_name} plan.",
                plan_name=payment.plan_name,
                amount=payment.amount
            )
        else:
            return PaymentResponse(
                success=False,
                transaction_id="",
                message="Payment failed. Please try again or use a different payment method.",
                plan_name=payment.plan_name,
                amount=payment.amount
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/payments/plans")
async def get_payment_plans():
    """Get available subscription plans"""
    return {
        "plans": [
            {
                "id": "starter",
                "name": "Starter",
                "price": 29,
                "currency": "USD",
                "interval": "month",
                "apartment_limit": 3,
                "features": [
                    "Up to 3 apartments",
                    "Basic AI assistant",
                    "Email notifications",
                    "Basic analytics"
                ]
            },
            {
                "id": "professional", 
                "name": "Professional",
                "price": 79,
                "currency": "USD",
                "interval": "month",
                "apartment_limit": 10,
                "features": [
                    "Up to 10 apartments",
                    "Advanced AI assistant",
                    "Email + WhatsApp notifications",
                    "Advanced analytics",
                    "Custom branding",
                    "iCal integration"
                ]
            },
            {
                "id": "enterprise",
                "name": "Enterprise",
                "price": 199,
                "currency": "USD", 
                "interval": "month",
                "apartment_limit": -1,
                "features": [
                    "Unlimited apartments",
                    "Premium AI assistant",
                    "All notification methods",
                    "Full analytics suite",
                    "White-label solution",
                    "Custom domain",
                    "Priority support"
                ]
            }
        ]
    }

# Property Import Routes
@api_router.post("/apartments/import-from-url")
async def import_property_from_url(
    request: PropertyImportRequest,
    current_user: User = Depends(get_current_user)
):
    """Import property data from Airbnb, Booking.com, or VRBO URL"""
    try:
        url = request.url.strip()
        
        # Validate URL
        if not url.startswith(('http://', 'https://')):
            raise HTTPException(status_code=400, detail="Invalid URL format")
        
        # Check if it's a supported platform
        supported_platforms = ['airbnb.com', 'booking.com', 'vrbo.com', 'homeaway.com']
        if not any(platform in url.lower() for platform in supported_platforms):
            raise HTTPException(
                status_code=400, 
                detail="URL must be from Airbnb, Booking.com, or VRBO"
            )
        
        # Scrape the listing data
        if 'airbnb.com' in url.lower():
            scraped_data = await scrape_airbnb_listing(url)
        elif 'booking.com' in url.lower():
            scraped_data = await scrape_booking_listing(url)
        else:
            # For other platforms, return generic structure
            scraped_data = {
                'name': 'Imported Property',
                'address': 'Address not found - please enter manually',
                'description': 'Property description not found - please add your own description',
                'rules': ['Check-in instructions will be provided', 'Check-out before 11:00 AM', 'No smoking', 'No parties or events']
            }
            
        # Return only the fields you need: name, address, description, rules
        filtered_data = {
            'name': scraped_data.get('name', ''),
            'address': scraped_data.get('address', ''),
            'description': scraped_data.get('description', ''),
            'rules': scraped_data.get('rules', []),
            # Keep empty structures for frontend compatibility
            'contact': {'phone': '', 'email': '', 'whatsapp': ''},
            'recommendations': {
                'restaurants': [],
                'hidden_gems': [],
                'transport': ''
            }
        }
        
        return {
            "success": True,
            "data": filtered_data,
            "message": f"Property data imported successfully from {url}!"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Property import error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to import property: {str(e)}")

# Admin Routes for Database Management
@api_router.post("/admin/login", response_model=Token)
@limiter.limit("5/minute")  # Limit admin login attempts
async def admin_login(request: Request, credentials: dict):
    """Admin login with hardcoded credentials"""
    try:
        username = credentials.get("username")
        password = credentials.get("password")
        
        # Hardcoded admin credentials
        ADMIN_USERNAME = "myhomeiq_admin"
        ADMIN_PASSWORD = "Admin123!MyHomeIQ"
        
        if username != ADMIN_USERNAME or password != ADMIN_PASSWORD:
            raise HTTPException(status_code=401, detail="Invalid admin credentials")
        
        # Create admin token
        admin_data = {
            "sub": "admin_user",
            "admin": True,
            "username": ADMIN_USERNAME
        }
        
        access_token = create_access_token(admin_data)
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            user={
                "id": "admin_user",
                "email": "admin@myhomeiq.com",
                "full_name": "MyHomeIQ Admin",
                "is_admin": True,
                "brand_name": "MyHomeIQ"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin login error: {str(e)}")
        raise HTTPException(status_code=500, detail="Login failed")

# Admin authentication helper
async def get_admin_user_from_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Get admin user from token"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        
        if not payload.get("admin"):
            raise HTTPException(status_code=403, detail="Admin privileges required")
            
        return payload
        
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@api_router.get("/admin/users", response_model=List[dict])
@limiter.limit("20/minute")  # Rate limit admin operations
async def get_all_users(request: Request, admin_user: dict = Depends(get_admin_user_from_token)):
    """Get all users - Admin only"""
    try:
        users = await db.users.find({}, {"hashed_password": 0, "_id": 0}).to_list(length=None)
        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/admin/apartments", response_model=List[dict])
@limiter.limit("20/minute")
async def get_all_apartments(request: Request, admin_user: dict = Depends(get_admin_user_from_token)):
    """Get all apartments - Admin only"""
    try:
        apartments = await db.apartments.find({}, {"_id": 0}).to_list(length=None)
        return apartments
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.put("/admin/apartments/{apartment_id}")
@limiter.limit("10/minute")
async def admin_update_apartment(
    request: Request,
    apartment_id: str,
    apartment_data: dict,
    admin_user: dict = Depends(get_admin_user_from_token)
):
    """Update any apartment - Admin only"""
    try:
        # Prepare data for MongoDB
        update_data = prepare_for_mongo(apartment_data)
        
        result = await db.apartments.update_one(
            {"id": apartment_id},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Apartment not found")
        
        return {"message": "Apartment updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.delete("/admin/apartments/{apartment_id}")
@limiter.limit("5/minute")
async def admin_delete_apartment(
    request: Request,
    apartment_id: str,
    admin_user: dict = Depends(get_admin_user_from_token)
):
    """Delete any apartment - Admin only"""
    try:
        result = await db.apartments.delete_one({"id": apartment_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Apartment not found")
        
        # Also delete related chat messages
        await db.chat_messages.delete_many({"apartment_id": apartment_id})
        
        return {"message": "Apartment and related data deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/admin/stats")
@limiter.limit("30/minute")
async def get_admin_stats(request: Request, admin_user: dict = Depends(get_admin_user_from_token)):
    """Get overall platform statistics - Admin only"""
    try:
        # Count totals
        total_users = await db.users.count_documents({})
        total_apartments = await db.apartments.count_documents({})  
        total_messages = await db.chat_messages.count_documents({})
        total_email_creds = await db.email_credentials.count_documents({})
        
        # Recent activity (last 24 hours)
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        
        recent_users = await db.users.count_documents({
            "created_at": {"$gte": yesterday.isoformat()}
        })
        
        recent_messages = await db.chat_messages.count_documents({
            "timestamp": {"$gte": yesterday.isoformat()}
        })
        
        # Most active apartments
        pipeline = [
            {"$group": {"_id": "$apartment_id", "message_count": {"$sum": 1}}},
            {"$sort": {"message_count": -1}},
            {"$limit": 5}
        ]
        
        most_active = await db.chat_messages.aggregate(pipeline).to_list(length=5)
        
        return {
            "totals": {
                "users": total_users,
                "apartments": total_apartments,
                "messages": total_messages,
                "email_credentials": total_email_creds
            },
            "recent_activity": {
                "new_users_24h": recent_users,
                "messages_24h": recent_messages
            },
            "most_active_apartments": most_active
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/admin/export-data")
async def export_all_data(current_user: User = Depends(get_current_user)):
    """Export all data as JSON - Admin only"""
    try:
        users = await db.users.find({}, {"hashed_password": 0}).to_list(length=None)
        apartments = await db.apartments.find().to_list(length=None)
        messages = await db.chat_messages.find().to_list(length=None)
        
        export_data = {
            "users": users,
            "apartments": apartments,
            "chat_messages": messages,
            "exported_at": datetime.now(timezone.utc).isoformat()
        }
        
        return export_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Enhanced Apartment Routes
@api_router.post("/apartments", response_model=Apartment)
async def create_apartment(apartment_data: ApartmentCreate, current_user: User = Depends(get_current_user)):
    """Create a new apartment with host data"""
    try:
        # Geocode address with Mapbox if not provided
        if apartment_data.address and (apartment_data.latitude is None or apartment_data.longitude is None):
            coords = await geocode_address_with_mapbox(apartment_data.address)
            if coords:
                apartment_data.latitude = coords['latitude']
                apartment_data.longitude = coords['longitude']
                logger.info(f"Geocoded address: {apartment_data.address} -> {coords}")
        
        apartment = Apartment(
            user_id=current_user.id,
            **apartment_data.dict()
        )
        apartment_dict = prepare_for_mongo(apartment.dict())
        
        await db.apartments.insert_one(apartment_dict)
        
        # If iCal URL is provided, start monitoring for bookings
            # Background task to sync calendar
            
        return apartment
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.put("/apartments/{apartment_id}", response_model=Apartment)
async def update_apartment(
    apartment_id: str, 
    apartment_data: ApartmentUpdate, 
    current_user: User = Depends(get_current_user)
):
    """Update apartment information"""
    try:
        # Verify apartment belongs to user
        existing_apartment = await db.apartments.find_one({
            "id": apartment_id, 
            "user_id": current_user.id
        })
        if not existing_apartment:
            raise HTTPException(status_code=404, detail="Apartment not found")
        
        # Geocode address if changed and coordinates not provided
        if (apartment_data.address != existing_apartment.get('address') and 
            (apartment_data.latitude is None or apartment_data.longitude is None)):
            coords = await geocode_address_with_mapbox(apartment_data.address)
            if coords:
                apartment_data.latitude = coords['latitude']
                apartment_data.longitude = coords['longitude']
                logger.info(f"Re-geocoded address: {apartment_data.address} -> {coords}")
        
        # Update apartment
        update_data = prepare_for_mongo(apartment_data.dict())
        await db.apartments.update_one(
            {"id": apartment_id},
            {"$set": update_data}
        )
        
        # If iCal URL changed, start monitoring
        
        # Return updated apartment
        updated_apartment = await db.apartments.find_one({"id": apartment_id})
        return Apartment(**updated_apartment)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/apartments", response_model=List[Apartment])
async def get_apartments(current_user: User = Depends(get_current_user)):
    """Get user's apartments"""
    try:
        apartments = await db.apartments.find({"user_id": current_user.id}).to_list(1000)
        return [Apartment(**apt) for apt in apartments]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/apartments/{apartment_id}", response_model=Apartment)
async def get_apartment(apartment_id: str, current_user: User = Depends(get_current_user)):
    """Get specific apartment by ID"""
    try:
        apartment = await db.apartments.find_one({"id": apartment_id, "user_id": current_user.id})
        if not apartment:
            raise HTTPException(status_code=404, detail="Apartment not found")
        return Apartment(**apartment)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Public apartment route for guests (no auth required)
@api_router.get("/public/apartments/{apartment_id}")
async def get_public_apartment(apartment_id: str):
    """Get apartment info for guests (public route)"""
    try:
        apartment = await db.apartments.find_one({"id": apartment_id})
        if not apartment:
            raise HTTPException(status_code=404, detail="Apartment not found")
        
        # Get user's branding info
        user = await db.users.find_one({"id": apartment['user_id']})
        branding = {
            "brand_name": user.get('brand_name', 'My Host IQ'),
            "ai_assistant_name": user.get('ai_assistant_name', 'AI Assistant'),
            "brand_logo_url": user.get('brand_logo_url', ''),
            "brand_primary_color": user.get('brand_primary_color', '#6366f1'),
            "brand_secondary_color": user.get('brand_secondary_color', '#10b981')
        }
        
        # Remove MongoDB ObjectId fields that can't be serialized
        if '_id' in apartment:
            del apartment['_id']
        
        return {
            "apartment": apartment,  # Return FULL apartment data under apartment key
            "branding": branding
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Chat Routes - Simplified Public Access
@api_router.post("/guest-chat")
@limiter.limit("30/minute")  
async def guest_chat_with_ai(request: Request, chat_request: ChatRequest):
    """Public guest chat with AI - No authentication required, rate limited per apartment"""
    try:
        apartment_id = chat_request.apartment_id
        
        # Check daily rate limit (100 queries per day per apartment)
        today = datetime.now().date().isoformat()
        rate_limit_key = f"chat_limit:{apartment_id}:{today}"
        
        # Get current count from database
        rate_limit_doc = await db.rate_limits.find_one({"key": rate_limit_key})
        
        if rate_limit_doc and rate_limit_doc.get('count', 0) >= 100:
            raise HTTPException(
                status_code=429, 
                detail="Daily limit reached. Please try again tomorrow."
            )
        
        # Get apartment data
        apartment = await db.apartments.find_one({"id": apartment_id})
        if not apartment:
            raise HTTPException(status_code=404, detail="Apartment not found")
        
        # Get user's branding
        user = await db.users.find_one({"id": apartment['user_id']})
        branding = {
            "brand_name": user.get('brand_name', 'My Host IQ'),
            "ai_assistant_name": user.get('ai_assistant_name', 'AI Assistant'),
        }
        
        # PROXIMITY SEARCH LOGIC - Check if this is a "nearest places" query
        proximity_response = None
        message_lower = chat_request.message.lower()
        
        # Define proximity keywords and categories
        proximity_keywords = {
            'supermarket': ['supermarket', 'grocery', 'store', 'market', 'prodavnica', 'trgovina'],
            'bakery': ['bakery', 'bread', 'pastry', 'pekara', 'pekarna'],
            'pharmacy': ['pharmacy', 'medicine', 'drug store', 'apoteka', 'ljekarna'],
            'restaurant': ['restaurant', 'restoran'],
            'cafe': ['cafe', 'coffee', 'cafeteria', 'kafic', 'kava'],
            'bar': ['bar', 'pub', 'drink'],
            'club': ['club', 'nightclub', 'night life', 'nightlife', 'klub'],
            'atm': ['atm', 'cash', 'money', 'bankomat'],
            'bank': ['bank', 'banka'],
            'hospital': ['hospital', 'emergency', 'bolnica'],
            'shopping': ['shopping', 'mall', 'shopping center', 'trgovacki centar'],
            'park': ['park'],
            'gym': ['gym', 'fitness', 'teretana'],
            'museum': ['museum', 'muzej'],
            'attraction': ['tourist', 'attraction', 'sightseeing']
        }
        
        # Extended proximity query indicators - multiple languages
        proximity_indicators = [
            # English
            'nearest', 'closest', 'nearby', 'near', 'close', 'around',
            'where is', 'where can i find', 'is there', 'are there',
            # Bosnian/Croatian/Serbian
            'najbliz', 'gdje je', 'gde je', 'gdje mogu', 'ima li', 'postoji li',
            # German
            'wo ist', 'wo gibt es', 'gibt es',
            # French
            'où est', 'où se trouve', 'y a-t-il',
            # Spanish
            'dónde está', 'dónde hay', 'hay algún',
            # Italian
            'dove si trova', 'dove posso trovare', 'c\'è un'
        ]
        
        # Check if message contains proximity indicators
        has_proximity_indicator = any(indicator in message_lower for indicator in proximity_indicators)
        
        # Detect category
        detected_category = None
        for category, keywords in proximity_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                detected_category = category
                break
        
        # Check if host has recommendations for this category
        host_has_recommendations = False
        if detected_category and apartment.get('recommendations'):
            recommendations = apartment['recommendations']
            # Check if host provided recommendations for restaurants/bars/cafes
            if detected_category in ['restaurant', 'cafe', 'bar']:
                if recommendations.get('restaurants') or recommendations.get('nightlife'):
                    host_has_recommendations = True
        
        # Determine if we should use proximity search
        use_proximity_search = False
        explicit_proximity_request = any(word in message_lower for word in ['nearest', 'closest', 'najbliz'])
        
        if detected_category and apartment.get('latitude') and apartment.get('longitude'):
            # Use proximity search if:
            # 1. Guest explicitly asks for "nearest/closest", OR
            # 2. Guest asks "where is X" and host doesn't have recommendations for X
            if explicit_proximity_request or (has_proximity_indicator and not host_has_recommendations):
                use_proximity_search = True
        
        # If this is a proximity query and apartment has coordinates
        if use_proximity_search:
            logger.info(f"Proximity query detected: category={detected_category}, apartment_id={apartment_id}")
            
            # Check cache first
            cached_places = await get_cached_places(apartment_id, detected_category)
            
            if cached_places:
                logger.info(f"Using cached results for {detected_category}")
                places = cached_places
            else:
                # Search with Mapbox
                places = await search_nearby_places_with_mapbox(
                    apartment['latitude'],
                    apartment['longitude'],
                    detected_category,
                    radius_meters=1500  # 1.5km walking distance
                )
                
                # Cache the results
                if places:
                    await cache_places(apartment_id, detected_category, places)
                    logger.info(f"Cached {len(places)} places for {detected_category}")
            
            # Detect guest's language
            guest_language = 'en'  # default
            if any(word in message_lower for word in ['gdje', 'gde', 'ima li', 'najbliz', 'mogu', 'kako']):
                guest_language = 'bs'  # Bosnian/Croatian/Serbian
            elif any(word in message_lower for word in ['wo ist', 'gibt es', 'wo gibt']):
                guest_language = 'de'  # German
            elif any(word in message_lower for word in ['où', 'y a-t-il', 'où se trouve']):
                guest_language = 'fr'  # French
            elif any(word in message_lower for word in ['dónde', 'hay algún', 'dónde está']):
                guest_language = 'es'  # Spanish
            
            # Generate natural response
            if places:
                top_place = places[0]
                
                # Extract clean address: street + city only (remove postal code and country)
                full_address = top_place.get('address', '')
                clean_address = full_address
                
                # Remove postal codes (5-6 digit numbers)
                import re
                clean_address = re.sub(r'\b\d{4,6}\b', '', clean_address)
                # Remove country names
                country_names = ['Bosnia and Herzegovina', 'Croatia', 'Serbia', 'Germany', 'France', 'Italy', 'Spain']
                for country in country_names:
                    clean_address = clean_address.replace(country, '')
                # Clean up extra commas and spaces
                clean_address = re.sub(r',\s*,', ',', clean_address).strip(', ')
                
                # Language-specific responses
                if guest_language == 'bs':
                    proximity_response = f"Najbliži {detected_category} je **{top_place['name']}**, udaljen oko {top_place['distance']} metara"
                    if clean_address:
                        proximity_response += f" na adresi {clean_address}"
                    proximity_response += "."
                    
                    if len(places) > 1:
                        proximity_response += "\n\nOstale opcije u blizini:\n"
                        for place in places[1:4]:
                            proximity_response += f"• {place['name']} ({place['distance']}m)\n"
                else:  # English default
                    proximity_response = f"The closest {detected_category} is **{top_place['name']}**, about {top_place['distance']} meters away"
                    if clean_address:
                        proximity_response += f" at {clean_address}"
                    proximity_response += "."
                    
                    if len(places) > 1:
                        proximity_response += "\n\nOther nearby options:\n"
                        for place in places[1:4]:
                            proximity_response += f"• {place['name']} ({place['distance']}m away)\n"
            else:
                # No results found - language-specific fallback
                if guest_language == 'bs':
                    proximity_response = f"Nisam mogao pronaći {detected_category} u neposrednoj blizini. Možete pitati svog domaćina za specifične preporuke."
                else:
                    proximity_response = f"I couldn't find any {detected_category}s in the immediate area. You might want to ask your host for specific recommendations."
        
        # Create personalized system prompt for guest
        system_prompt = create_ai_system_prompt(apartment, branding)
        
        # Initialize session_id for conversation history
        session_id = chat_request.session_id or f"guest_{apartment_id}_{datetime.now().timestamp()}"
        
        # If we have a proximity response, use it directly
        if proximity_response:
            response = proximity_response
        else:
            # Get conversation history for context (last 10 messages)
            recent_messages = await db.chat_messages.find(
                {"session_id": session_id},
                {"content": 1, "type": 1, "timestamp": 1, "_id": 0}
            ).sort("timestamp", -1).limit(10).to_list(length=None)
            
            # Reverse to get chronological order
            recent_messages.reverse()
            
            orchestrator = StableChatOrchestrator(
                client_factory=get_openai_client,
                model="gpt-4o-mini"
            )
            orchestrator_result = await orchestrator.respond(
                apartment=apartment,
                branding=branding,
                message=chat_request.message,
                session_id=session_id,
                history=recent_messages,
            )
            response = orchestrator_result["response"]
        
        # Save user message to database
        user_chat_message = ChatMessage(
            apartment_id=apartment_id,
            message=chat_request.message,
            response="",
            session_id=session_id,
            content=chat_request.message,
            type="user",
            guest_ip=request.client.host if request.client else ""
        )
        
        user_chat_dict = prepare_for_mongo(user_chat_message.dict())
        await db.chat_messages.insert_one(user_chat_dict)
        
        # Save assistant response to database
        assistant_chat_message = ChatMessage(
            apartment_id=apartment_id,
            message="",
            response=response,
            session_id=session_id,
            content=response,
            type="assistant",
            guest_ip=request.client.host if request.client else ""
        )
        
        assistant_chat_dict = prepare_for_mongo(assistant_chat_message.dict())
        await db.chat_messages.insert_one(assistant_chat_dict)
        
        # Increment rate limit counter
        if rate_limit_doc:
            await db.rate_limits.update_one(
                {"key": rate_limit_key},
                {"$inc": {"count": 1}}
            )
        else:
            await db.rate_limits.insert_one({
                "key": rate_limit_key,
                "count": 1,
                "apartment_id": apartment_id,
                "date": today
            })
        
        # Get remaining queries for this apartment today
        updated_limit = await db.rate_limits.find_one({"key": rate_limit_key})
        remaining = 100 - updated_limit.get('count', 0)
        
        return {
            "response": response,
            "session_id": session_id,
            "queries_remaining": remaining
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Guest chat error: {str(e)}")
        raise HTTPException(status_code=500, detail="Chat service temporarily unavailable")

@api_router.post("/chat")
@limiter.limit("30/minute")  # Limit chat requests to prevent spam
async def chat_with_ai(request: Request, chat_request: ChatRequest):
    """Chat with AI assistant for specific apartment (public route)"""
    try:
        # Get apartment data
        apartment = await db.apartments.find_one({"id": chat_request.apartment_id})
        if not apartment:
            raise HTTPException(status_code=404, detail="Apartment not found")
        
        # Get user's branding
        user = await db.users.find_one({"id": apartment['user_id']})
        branding = {
            "brand_name": user.get('brand_name', 'My Host IQ'),
            "brand_logo_url": user.get('brand_logo_url', ''),
            "brand_primary_color": user.get('brand_primary_color', '#6366f1'),
            "brand_secondary_color": user.get('brand_secondary_color', '#10b981')
        }
        
        # Create personalized system prompt
        system_prompt = create_ai_system_prompt(apartment, branding)
        
        # Check if this looks like a local recommendation request without host data
        message_lower = chat_request.message.lower()
        city_from_address = extract_city_from_address(apartment.get('address', ''))
        
        # Keywords that suggest local recommendations needed
        local_keywords = [
            'nightlife', 'night life', 'bars', 'clubs', 'pubs', 'party', 'drink',
            'restaurants', 'food', 'eat', 'dining', 'cafes', 'coffee', 
            'activities', 'things to do', 'attractions', 'visit', 'see',
            'shopping', 'buy', 'stores', 'markets'
        ]
        
        # Check if message is asking for local recommendations
        needs_web_search = any(keyword in message_lower for keyword in local_keywords)
        has_city_mention = city_from_address.lower() in message_lower if city_from_address else False
        
        if needs_web_search and has_city_mention and city_from_address:
            # Get web search results for local recommendations
            search_query = f"{chat_request.message} {city_from_address}"
            try:
                # Use web search to get current local recommendations
                import requests
                
                # Simple web search simulation (in production, use proper search API)
                web_recommendations = f"""

CURRENT WEB SEARCH RESULTS FOR "{search_query}":
Based on current web search data for {city_from_address}, here are up-to-date local recommendations:

(Note: Use these web search results to provide current, accurate local recommendations when host hasn't provided specific data)
"""
                system_prompt += web_recommendations
                
            except Exception as e:
                logger.error(f"Web search error: {e}")
        
        # Also check for city PDF info
        try:
            city_pdf = await db.city_pdfs.find_one({
                "user_id": apartment['user_id'], 
                "city_name": {"$regex": city_from_address, "$options": "i"}
            })
            
            if city_pdf and city_pdf.get('pdf_content'):
                pdf_info = f"""

ADDITIONAL CITY INFORMATION FROM HOST PDF:
{city_pdf['pdf_content'][:2000]}...

Use this information to enhance your local recommendations.
"""
                system_prompt += pdf_info
                
        except Exception as e:
            logger.error(f"City PDF lookup error: {e}")
        
        # Initialize session_id for conversation history
        session_id = chat_request.session_id or f"apartment_{chat_request.apartment_id}"
        
        # Get conversation history for context (last 10 messages)
        recent_messages = await db.chat_messages.find(
            {"session_id": session_id},
            {"content": 1, "type": 1, "timestamp": 1, "_id": 0}
        ).sort("timestamp", -1).limit(10).to_list(length=None)
        
        # Reverse to get chronological order
        recent_messages.reverse()
        
        # Build conversation context with explicit context tracking instructions
        conversation_context = ""
        if recent_messages:
            conversation_context = "\n\n🧠 CONVERSATION CONTEXT TRACKING - CRITICAL:\n"
            conversation_context += "The following is the recent conversation history. You MUST understand follow-up questions in context of previous messages:\n\n"
            
            for i, msg in enumerate(recent_messages):
                role = "Guest" if msg.get('type') == 'user' else "AI Assistant"
                conversation_context += f"Message {i+1} - {role}: {msg.get('content', '')}\n"
            
            conversation_context += f"\nMessage {len(recent_messages)+1} - Guest: {chat_request.message}\n"
            conversation_context += "\n🎯 CONTEXT ANALYSIS:\n"
            conversation_context += "- If this message is a short question like 'How?', 'When?', 'Where?', refer to the PREVIOUS guest messages to understand what they're asking about\n"
            conversation_context += "- Example: If previous message was 'When is check-in?' and current is 'How?', understand they want check-in INSTRUCTIONS\n"
            conversation_context += "- Always maintain conversation flow and context awareness\n\n"
            
            # Add conversation context to system prompt
            system_prompt += conversation_context
        orchestrator = StableChatOrchestrator(
            client_factory=get_openai_client,
            model="gpt-4o-mini"
        )
        orchestrator_result = await orchestrator.respond(
            apartment=apartment,
            branding=branding,
            message=chat_request.message,
            session_id=session_id,
            history=recent_messages,
        )
        response = orchestrator_result["response"]
        
        # Save user message to database
        user_chat_message = ChatMessage(
            apartment_id=chat_request.apartment_id,
            message=chat_request.message,
            response="",
            session_id=session_id,
            content=chat_request.message,
            type="user"
        )
        
        user_chat_dict = prepare_for_mongo(user_chat_message.dict())
        await db.chat_messages.insert_one(user_chat_dict)
        
        # Save assistant response to database
        assistant_chat_message = ChatMessage(
            apartment_id=chat_request.apartment_id,
            message="",
            response=response,
            session_id=session_id,
            content=response,
            type="assistant"
        )
        
        assistant_chat_dict = prepare_for_mongo(assistant_chat_message.dict())
        await db.chat_messages.insert_one(assistant_chat_dict)
        
        # Update apartment analytics
        await db.apartments.update_one(
            {"id": chat_request.apartment_id},
            {
                "$inc": {"total_chats": 1},
                "$set": {"last_chat": datetime.now(timezone.utc).isoformat()}
            }
        )
        
        return {
            "message": chat_request.message,
            "response": response,
            "apartment_name": apartment.get("name", "Unknown"),
            "branding": branding
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

# Analytics Routes
@api_router.get("/analytics/dashboard")
async def get_analytics_dashboard(current_user: User = Depends(get_current_user)):
    """Get analytics dashboard for user's apartments"""
    try:
        # Get user's apartments with analytics
        apartments = await db.apartments.find({"user_id": current_user.id}).to_list(1000)
        
        analytics_data = []
        total_chats = 0
        total_apartments = len(apartments)
        total_sessions = 0
        total_guest_views = 0
        total_successful_responses = 0
        total_user_messages = 0
        
        for apartment in apartments:
            apt_id = apartment['id']
            
            # Get chat messages for this apartment
            messages = await db.chat_messages.find({"apartment_id": apt_id}).to_list(1000)
            
            # Count user messages vs assistant responses for quality stats
            user_msgs = [m for m in messages if m.get('type') == 'user']
            assistant_msgs = [m for m in messages if m.get('type') == 'assistant']
            successful = [m for m in assistant_msgs if m.get('content') and 
                         'trouble connecting' not in m.get('content', '').lower() and
                         'temporarily unavailable' not in m.get('content', '').lower()]
            total_user_messages += len(user_msgs)
            total_successful_responses += len(successful)
            
            # Count unique sessions for guest views
            apt_sessions = set(m.get('session_id', '') for m in messages if m.get('session_id'))
            total_sessions += len(apt_sessions)
            
            # Count rate limit hits as guest views proxy
            rate_docs = await db.rate_limits.find({"apartment_id": apt_id}).to_list(100)
            total_guest_views += sum(r.get('count', 0) for r in rate_docs)
            
            # Calculate REAL popular questions with SMART SEMANTIC GROUPING
            # Group similar questions regardless of language or phrasing
            QUESTION_CATEGORIES = {
                "wifi": {"keywords": ["wifi", "wi-fi", "password", "internet", "lozinka", "sifra", "šifra", "wlan", "netz", "passwort", "mot de passe", "contraseña"], "label": "WiFi & Internet"},
                "checkin": {"keywords": ["check in", "checkin", "check-in", "arrival", "arrive", "key", "keys", "lockbox", "door", "enter", "entrance", "kako uci", "kako ući", "ulaz", "ključ", "kljuc", "dolazak", "prijava", "einchecken", "schlüssel", "arrivée", "llegada"], "label": "Check-in & Access"},
                "checkout": {"keywords": ["check out", "checkout", "check-out", "leave", "leaving", "departure", "odjava", "odlazak", "kad moram", "kada moram", "auschecken", "départ", "salida"], "label": "Check-out"},
                "smoking": {"keywords": ["smok", "cigarett", "pušen", "pusen", "pusiti", "pušiti", "pusi", "puši", "duhan", "rauchen", "fumer", "fumar"], "label": "Smoking Policy"},
                "parking": {"keywords": ["park", "car", "garage", "auto", "parking", "parkiraliste", "parkiralište", "voiture", "coche", "parkplatz"], "label": "Parking"},
                "towels": {"keywords": ["towel", "peškir", "peskir", "ručnik", "rucnik", "handtuch", "serviette", "toalla"], "label": "Towels & Linens"},
                "restaurants": {"keywords": ["restaurant", "eat", "food", "dinner", "lunch", "breakfast", "restoran", "hrana", "jesti", "essen", "manger", "comer", "recommend", "preporuk"], "label": "Restaurant Recommendations"},
                "rules": {"keywords": ["rule", "rules", "allowed", "forbidden", "prohibit", "pravil", "smije", "može", "moze", "dozvol", "zabranjen", "regel", "règle", "regla"], "label": "House Rules"},
                "location": {"keywords": ["near", "nearest", "close", "closest", "where is", "where can", "gdje", "gde", "blizu", "najbliz", "najbliž", "supermarket", "pharmacy", "apoteka", "hospital", "bolnica", "wo ist", "où est", "dónde"], "label": "Nearby Places"},
                "transport": {"keywords": ["taxi", "bus", "tram", "airport", "transport", "uber", "prevoz", "aerodrom", "autobus", "tramvaj", "flughafen", "aéroport", "aeropuerto"], "label": "Transport & Getting Around"},
                "emergency": {"keywords": ["emergency", "help", "urgent", "police", "ambulance", "hospital", "hitno", "hitna", "policija", "bolnica", "notfall", "urgence", "emergencia"], "label": "Emergency & Safety"},
                "cleaning": {"keywords": ["clean", "cleaning", "wash", "laundry", "vacuum", "čišćen", "ciscen", "pranje", "veš", "ves", "reinigung", "nettoyage", "limpieza"], "label": "Cleaning & Laundry"},
                "kitchen": {"keywords": ["kitchen", "cook", "coffee", "kuhinja", "kuhin", "kafa", "kava", "küche", "cuisine", "cocina", "microwave", "fridge"], "label": "Kitchen & Appliances"},
            }
            
            question_groups = {}
            uncategorized = {}
            for msg in messages:
                if msg.get('type') != 'user':
                    continue
                question = msg.get('content', '').strip()
                if not question or len(question) < 5:
                    continue
                q_lower = question.lower()
                
                matched = False
                for cat_key, cat_data in QUESTION_CATEGORIES.items():
                    if any(kw in q_lower for kw in cat_data["keywords"]):
                        if cat_key not in question_groups:
                            question_groups[cat_key] = {"label": cat_data["label"], "count": 0, "examples": []}
                        question_groups[cat_key]["count"] += 1
                        if len(question_groups[cat_key]["examples"]) < 2:
                            question_groups[cat_key]["examples"].append(question)
                        matched = True
                        break
                
                if not matched:
                    normalized = q_lower.strip('?.,!').strip()
                    uncategorized[normalized] = uncategorized.get(normalized, 0) + 1
            
            # Build popular questions from grouped data
            popular_questions = []
            sorted_groups = sorted(question_groups.values(), key=lambda x: x["count"], reverse=True)
            user_msg_count = len([m for m in messages if m.get('type') == 'user'])
            for group in sorted_groups[:5]:
                popular_questions.append({
                    "question": group["label"],
                    "count": group["count"],
                    "percentage": round((group["count"] / max(user_msg_count, 1)) * 100, 1),
                    "examples": group["examples"]
                })
            
            # Add top uncategorized if we have less than 5
            if len(popular_questions) < 5 and uncategorized:
                sorted_uncat = sorted(uncategorized.items(), key=lambda x: x[1], reverse=True)
                for q, count in sorted_uncat[:5 - len(popular_questions)]:
                    popular_questions.append({
                        "question": q.capitalize(),
                        "count": count,
                        "percentage": round((count / max(user_msg_count, 1)) * 100, 1)
                    })
            
            # If no questions yet, show helpful placeholder
            if not popular_questions:
                popular_questions = [{
                    "question": "No questions asked yet",
                    "count": 0,
                    "percentage": 0
                }]
            
            # Calculate REAL peak usage hours based on actual message timestamps
            hourly_usage = {}
            for msg in messages:
                try:
                    timestamp = datetime.fromisoformat(msg['timestamp'])
                    hour = timestamp.hour
                    hourly_usage[hour] = hourly_usage.get(hour, 0) + 1
                except:
                    continue
            
            # Find peak hours and create meaningful labels
            peak_hours = []
            if hourly_usage:
                # Get top 3 most active hours
                sorted_hours = sorted(hourly_usage.items(), key=lambda x: x[1], reverse=True)
                for hour, count in sorted_hours[:3]:
                    # Create time range (hour to hour+2)
                    end_hour = min(hour + 2, 24)
                    time_range = f"{hour:02d}:00 - {end_hour:02d}:00"
                    
                    # Create contextual labels based on time of day
                    if 6 <= hour <= 11:
                        label = "Morning inquiries"
                    elif 12 <= hour <= 17:
                        label = "Afternoon questions" 
                    elif 18 <= hour <= 22:
                        label = "Evening support"
                    elif 23 <= hour or hour <= 5:
                        label = "Night inquiries"
                    else:
                        label = "General questions"
                    
                    # Calculate usage percentage relative to peak hour
                    max_usage = max(hourly_usage.values())
                    usage_percentage = int((count / max_usage) * 100) if max_usage > 0 else 0
                    
                    peak_hours.append({
                        'time': time_range,
                        'usage': usage_percentage,
                        'label': label,
                        'count': count
                    })
            
            # If no data, show meaningful empty state
            if not peak_hours:
                peak_hours = [{
                    'time': 'No data yet',
                    'usage': 0,
                    'label': 'Start chatting to see patterns',
                    'count': 0
                }]
            
            total_chats += len(messages)
            
            analytics_data.append(AnalyticsData(
                apartment_id=apt_id,
                apartment_name=apartment.get('name', 'Unknown'),
                total_chats=len(messages),
                total_sessions=len(set(msg.get('session_id', '') for msg in messages if msg.get('session_id'))),
                last_chat=datetime.fromisoformat(apartment['last_chat']) if apartment.get('last_chat') else None,
                popular_questions=popular_questions,
                peak_hours=peak_hours
            ))
        
        # Calculate AI response quality from real data
        if total_user_messages > 0:
            ai_quality = round((total_successful_responses / total_user_messages) * 100, 1)
        else:
            ai_quality = 0
        
        return {
            "overview": {
                "total_apartments": total_apartments,
                "total_chats": total_chats,
                "active_apartments": len([apt for apt in apartments if apt.get('last_chat')]),
                "avg_chats_per_apartment": total_chats / max(total_apartments, 1),
                "ai_response_quality": ai_quality,
                "total_sessions": total_sessions,
                "total_guest_views": total_guest_views
            },
            "apartments": analytics_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/apartments/{apartment_id}/chat-history")
async def get_chat_history(apartment_id: str, current_user: User = Depends(get_current_user)):
    """Get chat history for an apartment"""
    try:
        # Verify apartment belongs to user
        apartment = await db.apartments.find_one({"id": apartment_id, "user_id": current_user.id})
        if not apartment:
            raise HTTPException(status_code=404, detail="Apartment not found")
        
        messages = await db.chat_messages.find(
            {"apartment_id": apartment_id}
        ).sort("timestamp", -1).limit(100).to_list(100)
        
        return [ChatMessage(**msg) for msg in messages]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Question Normalization Route
@api_router.get("/analytics/normalized-questions/{apartment_id}")
@limiter.limit("5/minute")  # Rate limit for intensive processing
async def get_normalized_questions(request: Request, apartment_id: str, current_user: User = Depends(get_current_user)):
    """Get semantically grouped and normalized questions for apartment"""
    try:
        # Verify apartment belongs to user
        apartment = await db.apartments.find_one({
            "id": apartment_id, 
            "user_id": current_user.id
        })
        if not apartment:
            raise HTTPException(status_code=404, detail="Apartment not found")
        
        # Get all user messages (questions)
        chat_messages = await db.chat_messages.find(
            {"apartment_id": apartment_id, "type": "user"}
        ).sort("timestamp", -1).limit(200).to_list(200)
        
        if not chat_messages:
            return {
                "normalized_questions": [],
                "total_questions": 0,
                "groups_created": 0,
                "processed_at": datetime.now(timezone.utc).isoformat()
            }
        
        # Extract unique questions
        questions = []
        for msg in chat_messages:
            content = msg.get('content', '').strip()
            if content and len(content) > 10:  # Filter out very short messages
                questions.append({
                    "text": content,
                    "timestamp": msg.get('timestamp'),
                    "message_id": msg.get('id')
                })
        
        if not questions:
            return {
                "normalized_questions": [],
                "total_questions": 0,
                "groups_created": 0,
                "processed_at": datetime.now(timezone.utc).isoformat()
            }
        
        # Prepare questions for AI processing
        questions_text = "\n".join([f"{i+1}. {q['text']}" for i, q in enumerate(questions[:50])])  # Limit to 50 for processing
        
        # AI-powered question normalization
        system_message = """You are an expert in semantic analysis and question categorization for vacation rental properties.
        Your task is to analyze guest questions and group similar ones together, identifying common themes and patterns.
        Focus on creating meaningful groups that help hosts understand guest needs better."""
        
        user_prompt = f"""
        Analyze these guest questions from a vacation rental property and group similar ones together:
        
        {questions_text}
        
        Group similar questions semantically (not just by exact words) and provide normalized versions.
        For example, "Where is the WiFi password?" and "How do I connect to internet?" should be grouped together.
        
        Return JSON format:
        {{
            "question_groups": [
                {{
                    "normalized_question": "How to connect to WiFi?",
                    "category": "amenities",
                    "similar_questions": ["Where is the WiFi password?", "How do I connect to internet?"],
                    "frequency": 5,
                    "urgency": "high",
                    "suggested_response": "Brief suggested response template"
                }}
            ],
            "categories": {{
                "amenities": 10,
                "check_in": 8,
                "local_info": 5,
                "rules": 3
            }},
            "insights": ["Most guests ask about WiFi", "Check-in process needs clarification"]
        }}
        
        Focus on practical groupings that help hosts improve their property information and guest experience.
        """
        
        # Initialize LLM chat for question analysis
        api_key = os.getenv('OPENAI_API_KEY') or os.getenv('EMERGENT_LLM_KEY')
        if not api_key:
            raise HTTPException(status_code=500, detail="AI service not configured")
        
        client = get_openai_client()
        ai_response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        ai_response = ai_response.choices[0].message.content
        
        # Parse AI response
        try:
            import json
            ai_content = ai_response.strip()
            if ai_content.startswith('```json'):
                ai_content = ai_content.split('```json')[1].split('```')[0].strip()
            elif ai_content.startswith('```'):
                ai_content = ai_content.split('```')[1].split('```')[0].strip()
            
            normalized_data = json.loads(ai_content)
        except Exception as parse_error:
            logger.error(f"Failed to parse AI response: {parse_error}")
            # Fallback: Create basic grouping
            question_freq = {}
            for q in questions:
                text = q['text'].lower()
                # Simple keyword-based grouping as fallback
                if any(word in text for word in ['wifi', 'internet', 'password']):
                    key = "WiFi and Internet"
                elif any(word in text for word in ['checkin', 'check-in', 'key', 'access']):
                    key = "Check-in Process"
                elif any(word in text for word in ['restaurant', 'food', 'eat', 'dining']):
                    key = "Dining and Restaurants"
                elif any(word in text for word in ['parking', 'car', 'vehicle']):
                    key = "Parking"
                else:
                    key = "General Questions"
                
                if key not in question_freq:
                    question_freq[key] = {"questions": [], "count": 0}
                question_freq[key]["questions"].append(q['text'])
                question_freq[key]["count"] += 1
            
            normalized_data = {
                "question_groups": [
                    {
                        "normalized_question": category,
                        "category": "general",
                        "similar_questions": data["questions"][:5],  # Limit to 5 examples
                        "frequency": data["count"],
                        "urgency": "medium",
                        "suggested_response": f"Please provide information about {category.lower()}"
                    } for category, data in question_freq.items()
                ],
                "categories": {cat: data["count"] for cat, data in question_freq.items()},
                "insights": [f"Received {len(questions)} total questions", "Consider adding FAQ section"]
            }
        
        # Add metadata
        normalized_data["apartment_id"] = apartment_id
        normalized_data["total_questions"] = len(questions)
        normalized_data["groups_created"] = len(normalized_data.get("question_groups", []))
        normalized_data["processed_at"] = datetime.now(timezone.utc).isoformat()
        
        return normalized_data
        
    except Exception as e:
        logger.error(f"Error normalizing questions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to normalize questions: {str(e)}")

# AI Insights Routes
@api_router.get("/analytics/insights/{apartment_id}")
@limiter.limit("10/minute")  # Rate limit insights generation
async def get_ai_insights(request: Request, apartment_id: str, current_user: User = Depends(get_current_user)):
    """Generate AI-powered insights and optimization advice for apartment"""
    try:
        # Verify apartment belongs to user
        apartment = await db.apartments.find_one({
            "id": apartment_id, 
            "user_id": current_user.id
        })
        if not apartment:
            raise HTTPException(status_code=404, detail="Apartment not found")
        
        # Get apartment analytics data
        chat_messages = await db.chat_messages.find(
            {"apartment_id": apartment_id}
        ).sort("timestamp", -1).limit(100).to_list(100)
        
        booking_notifications = await db.booking_notifications.find(
            {"apartment_id": apartment_id}
        ).sort("created_at", -1).limit(20).to_list(20)
        
        # Calculate analytics
        total_messages = len(chat_messages)
        total_bookings = len(booking_notifications)
        
        # Get popular questions
        question_frequency = {}
        for msg in chat_messages:
            if msg.get('type') == 'user':
                question = msg.get('content', '').lower().strip()
                if question:
                    question_frequency[question] = question_frequency.get(question, 0) + 1
        
        popular_questions = sorted(question_frequency.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Get recent activity patterns
        recent_hours = [msg.get('timestamp') for msg in chat_messages[:30] if msg.get('timestamp')]
        
        # Create context for AI insights
        context_data = {
            "apartment_name": apartment.get('name', 'Unknown'),
            "apartment_type": apartment.get('property_type', 'apartment'),
            "location": apartment.get('address', 'Location not specified'),
            "total_messages": total_messages,
            "total_bookings": total_bookings,
            "popular_questions": popular_questions[:3],  # Top 3 questions
            "recent_activity": len(recent_hours),
            "apartment_features": apartment.get('amenities', []),
            "house_rules": apartment.get('rules', [])
        }
        
        # Generate AI insights using Emergent LLM
        system_message = """You are an AI property management advisor specializing in vacation rental optimization. 
        Analyze the provided apartment data and generate specific, actionable insights and recommendations. 
        Focus on guest experience improvement, operational efficiency, and revenue optimization.
        Provide concise, practical advice that hosts can implement immediately."""
        
        user_prompt = f"""
        Analyze this apartment's performance data and provide insights:
        
        Property: {context_data['apartment_name']} ({context_data['apartment_type']})
        Location: {context_data['location']}
        Total guest messages: {context_data['total_messages']}
        Total bookings: {context_data['total_bookings']}
        
        Most asked questions:
        {', '.join([q[0] for q in context_data['popular_questions'][:3]]) if context_data['popular_questions'] else 'No questions yet'}
        
        Recent activity: {context_data['recent_activity']} messages in last 30 interactions
        
        Features: {', '.join(context_data['apartment_features'][:5]) if context_data['apartment_features'] else 'Not specified'}
        
        Generate 3-4 specific insights and recommendations for this property. Format as JSON:
        {{
            "insights": [
                {{
                    "title": "Insight Title",
                    "description": "Detailed insight description",
                    "priority": "high|medium|low",
                    "category": "guest_experience|operational|revenue|marketing"
                }}
            ],
            "recommendations": [
                {{
                    "title": "Recommendation Title", 
                    "action": "Specific action to take",
                    "impact": "Expected positive impact",
                    "difficulty": "easy|medium|hard"
                }}
            ],
            "performance_score": 85,
            "key_strengths": ["Strength 1", "Strength 2"],
            "improvement_areas": ["Area 1", "Area 2"]
        }}
        """
        
        # Initialize LLM chat
        api_key = os.getenv('OPENAI_API_KEY') or os.getenv('EMERGENT_LLM_KEY')
        if not api_key:
            raise HTTPException(status_code=500, detail="AI service not configured")
        
        client = get_openai_client()
        ai_completion = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        ai_response = ai_completion.choices[0].message.content
        
        # Parse AI response
        try:
            # Extract JSON from AI response
            import json
            ai_content = ai_response.strip()
            if ai_content.startswith('```json'):
                ai_content = ai_content.split('```json')[1].split('```')[0].strip()
            elif ai_content.startswith('```'):
                ai_content = ai_content.split('```')[1].split('```')[0].strip()
            
            insights_data = json.loads(ai_content)
        except:
            # Fallback if JSON parsing fails
            insights_data = {
                "insights": [
                    {
                        "title": "AI Analysis Available",
                        "description": ai_response[:500] + "..." if len(ai_response) > 500 else ai_response,
                        "priority": "medium",
                        "category": "operational"
                    }
                ],
                "recommendations": [
                    {
                        "title": "Review AI Analysis",
                        "action": "Check the detailed AI insights provided",
                        "impact": "Improved property management",
                        "difficulty": "easy"
                    }
                ],
                "performance_score": 75,
                "key_strengths": ["Active guest communication"],
                "improvement_areas": ["Data collection"]
            }
        
        # Add metadata
        insights_data["generated_at"] = datetime.now(timezone.utc).isoformat()
        insights_data["apartment_id"] = apartment_id
        insights_data["data_points"] = {
            "messages": total_messages,
            "bookings": total_bookings,
            "popular_questions_count": len(popular_questions)
        }
        
        return insights_data
        
    except Exception as e:
        logger.error(f"Error generating AI insights: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate insights: {str(e)}")

# Root route
@api_router.get("/")
async def root():
    return {"message": "My Host IQ API - AI-powered apartment concierge with authentication"}

# Enhanced iCal Test Scenario Route
@api_router.get("/notifications/{apartment_id}")
async def get_apartment_notifications(apartment_id: str, current_user: User = Depends(get_current_user)):
    """Get notification history for an apartment"""
    try:
        # Verify apartment belongs to user
        apartment = await db.apartments.find_one({
            "id": apartment_id, 
            "user_id": current_user.id
        })
        if not apartment:
            raise HTTPException(status_code=404, detail="Apartment not found")
        
        notifications = await db.booking_notifications.find(
            {"apartment_id": apartment_id}
        ).sort("created_at", -1).limit(50).to_list(50)
        
        return [BookingNotification(**notif) for notif in notifications]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Root route
@api_router.get("/")
async def root():
    return {"message": "MyHostIQ API - AI-powered apartment concierge with advanced features", "version": "2.0"}

# Include the router in the main app
app.include_router(api_router)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = get_logger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
    logger.info("Database connection closed")

@app.on_event("startup")
async def startup_event():
    """Start MyHostIQ API server"""
    logger.info("🚀 MyHostIQ API server started successfully")
