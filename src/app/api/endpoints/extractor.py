from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.app.db.session import get_db
from src.app.models.models import ExtractedFields as ExtractedFieldsModel
from src.app.schemas.schemas import ExtractedFields, ExtractedFieldsCreate
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from src.app.core.config import settings
import logging
from sqlalchemy.sql import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Define request model for /extract endpoint
class ExtractRequest(BaseModel):
    job_url: str = Field(description="The URL of the job application page")

# Define Pydantic model for structured output
class FormField(BaseModel):
    type: str = Field(description="Type of the form field (e.g., text, email, select)")
    required: bool = Field(description="Whether the field is required")
    placeholder: Optional[str] = Field(default=None, description="Placeholder text if present")
    label: Optional[str] = Field(default=None, description="Associated label text if present")
    options: Optional[List[str]] = Field(default=None, description="Options for select fields")

class FormFields(BaseModel):
    fields: Dict[str, FormField] = Field(description="Dictionary of field names and their properties")

# Initialize LangChain chat model
chat_model = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.7,
    api_key=settings.OPENAI_API_KEY
)

def get_db_session():
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()

@router.post("/extract", response_model=ExtractedFields)
async def extract_fields(request: ExtractRequest, db: Session = Depends(get_db_session)):
    job_url = request.job_url
    logger.info(f"Processing job URL: {job_url}")
    driver = None
    try:
        # Set up Selenium with headless browser
        chrome_options = Options()
        chrome_options.headless = True  # Headless for extraction
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # Open the job application page
        driver.get(job_url)

        # Wait for any input field to ensure the form is loaded
        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input, textarea, select"))
            )
        except Exception as e:
            logger.warning(f"Form fields not found after waiting: {str(e)}")
            # Log the page source for debugging
            logger.debug(f"Page source snippet: {driver.page_source[:1000]}...")

        # Get the page source after JavaScript rendering
        html_content = driver.page_source
        soup = BeautifulSoup(html_content, "html.parser")

        # Extract form fields
        # Try finding a standard <form> tag first
        form = soup.find("form")
        if not form:
            # Fallback: Look for a container with form-like elements
            logger.info("Standard form tag not found, searching for form-like structure")
            form = soup.find(lambda tag: tag.name in ["div", "section", "main"] and tag.find_all(["input", "textarea", "select"]))
            if not form:
                # Last resort: Look for any container with multiple inputs
                form = soup.find(lambda tag: tag.name in ["div", "section", "main"] and len(tag.find_all(["input", "textarea", "select"])) > 1)
                if not form:
                    raise HTTPException(status_code=400, detail="No form or form-like structure found on the page")

        # Log the found form structure for debugging
        logger.debug(f"Found form structure snippet: {str(form)[:500]}...")

        fields = {}
        # Map input IDs to labels
        labels = {}
        for label in form.find_all("label"):
            for_id = label.get("for")
            if for_id:
                labels[for_id] = label.get_text(strip=True)

        # Extract inputs
        for input_tag in form.find_all(["input", "textarea", "select"]):
            name = input_tag.get("name")
            input_id = input_tag.get("id")
            if name:
                field_type = input_tag.get("type", "text") if input_tag.name != "select" else "select"
                required = "required" in input_tag.attrs
                placeholder = input_tag.get("placeholder", "")
                label = labels.get(input_id, None) if input_id else None
                options = None
                if field_type == "select":
                    options = [option.get("value") for option in input_tag.find_all("option") if option.get("value")]
                fields[name] = {
                    "type": field_type,
                    "required": required,
                    "placeholder": placeholder,
                    "label": label,
                    "options": options
                }

        # If no fields found, raise an error
        if not fields:
            raise HTTPException(status_code=400, detail="No form fields found on the page")

        # Optional LangChain refinement (disabled due to parsing issues)
        # For now, rely on BeautifulSoup extraction
        refined_fields_dict = fields

        # Save to database
        db_fields = ExtractedFieldsModel(job_url=job_url, fields=refined_fields_dict)
        db.add(db_fields)
        db.commit()
        db.refresh(db_fields)

        return ExtractedFields(
            id=db_fields.id,
            job_url=db_fields.job_url,
            fields=db_fields.fields,
            created_at=db_fields.created_at
        )

    except ValueError as e:
        logger.error(f"Invalid HTML structure: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid HTML structure: {str(e)}")
    except Exception as e:
        logger.error(f"Error extracting fields: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error extracting fields: {str(e)}")
    finally:
        if driver:
            driver.quit()

@router.get("/health")
async def check_db_connection(db: Session = Depends(get_db_session)):
    try:
        result = db.execute(text("SELECT COUNT(*) FROM extracted_fields")).scalar()
        return {"status": "success", "message": f"Database connected. Found {result} records in extracted_fields table."}
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to connect to the database")

@router.get("/records", response_model=List[ExtractedFields])
async def get_extracted_records(db: Session = Depends(get_db_session)):
    try:
        records = db.query(ExtractedFieldsModel).all()
        if not records:
            return []
        return [
            ExtractedFields(
                id=record.id,
                job_url=record.job_url,
                fields=record.fields,
                created_at=record.created_at
            )
            for record in records
        ]
    except Exception as e:
        logger.error(f"Error retrieving records: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving records: {str(e)}")