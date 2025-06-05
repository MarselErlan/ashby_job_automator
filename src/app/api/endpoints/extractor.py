from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.app.db.session import get_db
from src.app.models.models import ExtractedFields as ExtractedFieldsModel
from src.app.schemas.schemas import ExtractedFields, ExtractedFieldsCreate
import requests
from bs4 import BeautifulSoup
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize LangChain chat model
chat_model = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)

def get_db_session():
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()

@router.post("/extract", response_model=ExtractedFields)
async def extract_fields(job_url: str, db: Session = Depends(get_db_session)):
    try:
        # Fetch the webpage
        response = requests.get(job_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Extract form fields
        form = soup.find("form")
        if not form:
            raise HTTPException(status_code=400, detail="No form found on the page")

        fields = {}
        for input_tag in form.find_all(["input", "textarea", "select"]):
            name = input_tag.get("name")
            if name:
                field_type = input_tag.get("type", "text")
                required = "required" in input_tag.attrs
                placeholder = input_tag.get("placeholder", "")
                fields[name] = {
                    "type": field_type,
                    "required": required,
                    "placeholder": placeholder
                }

        # Use LangChain to refine field extraction
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", "You are a web scraping assistant. Identify required form fields and their types from the given HTML data. Return the result as a JSON string."),
            ("user", "HTML: {html}\nExtract required fields with their names, types, required status, and placeholders.")
        ])
        prompt = prompt_template.format_messages(html=str(form))
        refined_fields = chat_model.invoke(prompt).content

        # Parse refined fields
        try:
            refined_fields_dict = json.loads(refined_fields) if isinstance(refined_fields, str) else fields
        except json.JSONDecodeError:
            logger.warning("LangChain did not return valid JSON; falling back to initial extraction")
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

    except requests.RequestException as e:
        logger.error(f"Error fetching URL: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch URL: {str(e)}")
    except Exception as e:
        logger.error(f"Error extracting fields: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error extracting fields: {str(e)}")