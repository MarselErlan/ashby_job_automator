from fastapi import APIRouter, Depends, HTTPException, Query
from src.app.schemas.schemas import FillFormRequest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import logging
import os
import tempfile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/fill")
async def fill_form(
    request: FillFormRequest,
    close_browser: bool = Query(False, description="Whether to close the browser after filling the form")
):
    driver = None
    try:
        # Dummy profile
        dummy_profile = {
            "firstName": "John",
            "lastName": "Doe",
            "email": "john.doe@example.com",
            "phone": "123-456-7890",
            "resume": "dummy_resume.pdf",  # We'll create a dummy file
            "coverLetter": "I am excited to apply for this position at Wander. With my background in technology and passion for innovation, I believe I can contribute significantly to your team.",
            "linkedin": "https://linkedin.com/in/johndoe",
            "website": "https://johndoe.com",
            "portfolio": "https://portfolio.johndoe.com",
            "source": "linkedin"  # For dropdowns like "How did you hear about us?"
        }

        # Create a dummy resume file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(b"Dummy Resume for John Doe")
            dummy_profile["resume"] = temp_file.name

        # Set up Selenium with non-headless browser and automatic ChromeDriver management
        chrome_options = Options()
        chrome_options.headless = False  # Non-headless
        chrome_options.add_argument("--no-sandbox")  # Avoid permissions issues
        chrome_options.add_argument("--disable-dev-shm-usage")  # For macOS compatibility
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # Open the job application page
        driver.get(request.job_url)

        # Wait for specific form elements to be visible
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.NAME, "firstName"))
        )

        # Fill the form fields
        for field_name, field_info in request.fields.items():
            field_type = field_info.get("type", "text")
            required = field_info.get("required", False)
            options = field_info.get("options", [])
            if field_name in dummy_profile and dummy_profile[field_name]:
                try:
                    # Try locating by name with explicit wait
                    element = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.NAME, field_name))
                    )
                    if field_type in ["text", "email", "tel", "url"]:
                        element.clear()
                        element.send_keys(dummy_profile[field_name])
                    elif field_type == "textarea":
                        element.clear()
                        element.send_keys(dummy_profile[field_name])
                    elif field_type == "file":
                        element.send_keys(dummy_profile[field_name])
                    elif field_type == "select" and options:
                        select = Select(element)
                        select.select_by_value(dummy_profile[field_name].lower())
                    elif field_type == "checkbox":
                        if not element.is_selected():
                            element.click()
                    logger.info(f"Filled field {field_name} with value {dummy_profile[field_name]}")
                except Exception as e:
                    logger.warning(f"Could not fill field {field_name}: {str(e)}")
                    if required:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Failed to fill required field {field_name}: {str(e)}"
                        )
            elif required:
                logger.warning(f"Required field {field_name} not found in dummy profile")
                raise HTTPException(
                    status_code=400,
                    detail=f"Required field {field_name} not provided in dummy profile"
                )

        return {"status": "Form filled successfully. Check the browser window."}

    except Exception as e:
        logger.error(f"Error filling form: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error filling form: {str(e)}")
    finally:
        # Clean up the dummy file
        if dummy_profile.get("resume") and os.path.exists(dummy_profile["resume"]):
            os.remove(dummy_profile["resume"])
        # Close the browser if requested
        if close_browser and driver:
            driver.quit()
        elif driver:
            logger.info("Browser left open for inspection")