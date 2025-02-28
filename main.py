import os
import html
import traceback
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import openai
from agents.openai_agent import OpenAIAgent
from utils.logging_config import get_logger, truncate_message
from utils.html_formatter import format_response_as_html

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Set up logging
logger = get_logger("api")

# Initialize FastAPI app
app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up templates
templates = Jinja2Templates(directory="templates")

# Initialize OpenAI agent
agent = OpenAIAgent(api_key=OPENAI_API_KEY)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Render the home page"""
    logger.info("Rendering home page")
    return templates.TemplateResponse("index.html", {
        "request": request,
        "model_display_name": agent.model_display_name,
        "display_name": agent.display_name
    })

@app.post("/send-message-htmx", response_class=HTMLResponse)
async def chat_htmx(request: Request, message: str = Form(...)):
    """Process a chat message and return the response as HTML
    
    Args:
        request: FastAPI request object
        message: User message
        
    Returns:
        HTML response with the AI message
    """
    timestamp = datetime.now().strftime("%I:%M %p")  # Format: 2:30 PM
    logger.debug(f"Generated timestamp: {timestamp}")
    
    try:
        logger.info("Received request at /send-message-htmx: %s", truncate_message(message))
        logger.debug("Request details: %s", request.headers)
        
        # Process message with OpenAI agent
        response = agent.process_message(message)
        
        # Format response as HTML using the formatter utility
        formatted_content = await format_response_as_html(response)
        
        # Add timestamp and wrap in message container
        html_response = f"""
        <div class="message bot-message">
            <div class="message-content">
                <p>{formatted_content}</p>
                <div class="message-timestamp">{timestamp}</div>
            </div>
        </div>
        """
        
        logger.info("Sending response: %s", truncate_message(response))
        return HTMLResponse(content=html_response)
        
    except ValueError as e:
        # Handle validation errors (e.g., empty message)
        logger.warning("Validation error: %s", str(e))
        error_html = f"""
        <div class="message bot-message error-message">
            <div class="message-content">
                <p>
                    <div class="font-bold">Invalid Input</div>
                    <div>{html.escape(str(e))}</div>
                </p>
                <div class="message-timestamp">{timestamp}</div>
            </div>
        </div>
        """
        return HTMLResponse(content=error_html, status_code=400)
        
    except openai.RateLimitError as e:
        # Handle rate limit errors
        logger.error("Rate limit error: %s", str(e))
        error_html = f"""
        <div class="message bot-message error-message">
            <div class="message-content">
                <div class="font-bold">Rate Limit Exceeded</div>
                <div>The AI service is currently busy. Please try again in a few moments.</div>
            </div>
            <div class="message-timestamp">{timestamp}</div>
        </div>
        """
        return HTMLResponse(content=error_html, status_code=429)
        
    except openai.AuthenticationError as e:
        # Handle authentication errors
        logger.error("Authentication error: %s", str(e))
        error_html = f"""
        <div class="message bot-message error-message">
            <div class="message-content">
                <div class="font-bold">Authentication Error</div>
                <div>There's an issue with the AI service authentication. Please contact support.</div>
            </div>
            <div class="message-timestamp">{timestamp}</div>
        </div>
        """
        return HTMLResponse(content=error_html, status_code=401)
        
    except openai.APIConnectionError as e:
        # Handle connection errors
        logger.error("API connection error: %s", str(e))
        error_html = f"""
        <div class="message bot-message error-message">
            <div class="message-content">
                <div class="font-bold">Connection Error</div>
                <div>Could not connect to the AI service. Please check your internet connection and try again.</div>
            </div>
            <div class="message-timestamp">{timestamp}</div>
        </div>
        """
        return HTMLResponse(content=error_html, status_code=503)
        
    except openai.Timeout as e:
        # Handle timeout errors
        logger.error("Timeout error: %s", str(e))
        error_html = f"""
        <div class="message bot-message error-message">
            <div class="message-content">
                <div class="font-bold">Request Timeout</div>
                <div>The AI service took too long to respond. Please try again.</div>
            </div>
            <div class="message-timestamp">{timestamp}</div>
        </div>
        """
        return HTMLResponse(content=error_html, status_code=504)
        
    except openai.APIError as e:
        # Handle general API errors
        logger.error("OpenAI API error: %s", str(e))
        error_html = f"""
        <div class="message bot-message error-message">
            <div class="message-content">
                <div class="font-bold">AI Service Error</div>
                <div>The AI service encountered an error. Please try again later.</div>
            </div>
            <div class="message-timestamp">{timestamp}</div>
        </div>
        """
        return HTMLResponse(content=error_html, status_code=500)
        
    except Exception as e:
        # Handle all other unexpected errors
        logger.error("Error processing message: %s", str(e), exc_info=True)
        error_html = f"""
        <div class="message bot-message error-message">
            <div class="message-content">
                <div class="font-bold">Unexpected Error</div>
                <div>Sorry, something went wrong: {html.escape(str(e))}</div>
            </div>
            <div class="message-timestamp">{timestamp}</div>
        </div>
        """
        return HTMLResponse(content=error_html, status_code=500)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    logger.debug("Health check requested")
    return {"status": "ok"}
