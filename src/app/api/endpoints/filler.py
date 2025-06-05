from fastapi import APIRouter, Depends, HTTPException
from src.app.schemas.schemas import FillFormRequest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/fill")
async def fill_form(request: FillFormRequest):
    try:
        # Dummy profile
        dummy_profile = {
            "firstName": "John",
            "lastName": "Doe",
            "email": "john.doe@example.com",
            "phone": "123-456-7890",
            "resume": None,  # Skip file uploads
            "coverLetter": "I am excited to apply for this position at Wander. With my background in technology and passion for innovation, I believe I can contribute significantly to your team.",
            "linkedin": "https://linkedin.com/in/johndoe",
            "website": "https://johndoe.com",
            "portfolio": "https://portfolio.johndoe.com"
        }

        # Set up Selenium with non-headless browser
        chrome_options = Options()
        chrome_options.headless = False  # Non-headless
        driver = webdriver.Chrome(options=chrome_options)

        # Open the job application page
        driver.get(request.job_url)
        time.sleep(2)  # Wait for page to load

        # Fill the form fields
        for field_name, field_info in request.fields.items():
            field_type = field_info.get("type", "text")
            required = field_info.get("required", False)
            if field_name in dummy_profile and dummy_profile[field_name]:
                try:
                    element = driver.find_element(By.NAME, field_name)
                    if field_type in ["text", "email", "tel", "url"]:
                        element.send_keys(dummy_profile[field_name])
                    elif field_type == "textarea":
                        element.send_keys(dummy_profile[field_name])
                    # Skip file uploads and other complex fields
                    logger.info(f"Filled field {field_name} with value {dummy_profile[field_name]}")
                except Exception as e:
                    logger.warning(f"Could not fill field {field_name}: {str(e)}")
            elif required:
                logger.warning(f"Required field {field_name} not found in dummy profile")

        # Do not submit; leave the browser open
        return {"status": "Form filled successfully. Check the browser window."}

    except Exception as e:
        logger.error(f"Error filling form: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error filling form: {str(e)}")
    finally:
        # Keep the browser open for user inspection
        pass