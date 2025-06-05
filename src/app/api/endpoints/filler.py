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
        # Dummy profile mapped to Ashby field names
        dummy_profile = {
            "_systemfield_name": "John Doe",
            "_systemfield_email": "john.doe@example.com",
            "phone": "123-456-7890",
            "resume": "dummy_resume.pdf",  # We'll create a dummy file
            "linkedin": "https://linkedin.com/in/johndoe",
            "website": "https://johndoe.com",
            "portfolio": "https://portfolio.johndoe.com",
            "09163395-e645-4ef2-a928-023753e45489": "Yes, I have extensive experience with remote work. It suits me well as I enjoy the flexibility and focus it provides.",
            "2a4b601a-8aea-4471-86cc-c031bf48971c": "$120,000",
            "2c6f8c17-1e66-4e96-a092-836efdc3b5c5": "I’m highly skilled in my field, with a proven track record of success. Being great means consistently delivering high-quality results and exceeding expectations.",
            "3ae7df1f-17de-4d1b-b731-c38f22e46656": "My ideal relationship with work involves a balance of autonomy, collaboration, and growth opportunities. I thrive in environments where I can contribute meaningfully while learning continuously.",
            "435dea9d-d702-4af5-99f9-f520fc7c76e5": "LinkedIn: https://linkedin.com/in/johndoe, GitHub: https://github.com/johndoe",
            "46a14898-77af-427f-9961-0ae9330565b8": "I see myself staying with my next company for at least 3-5 years, provided there are opportunities for growth and impact.",
            "51438187-1634-4359-909b-dfa2a8644cce": "Absolutely, I’m excited to join a dynamic startup and contribute to its growth.",
            "51e2778c-b255-4acb-817e-47f95fc7e0f1": "I approach difficult tasks by breaking them down into manageable steps, researching thoroughly, and collaborating with my team when needed.",
            "555f2203-ce9a-43c7-8f2d-e401ee0e1dc8": "My typical workday starts with a review of priorities, followed by focused work on key tasks, meetings for collaboration, and time for learning or research.",
            "5dd27251-0fb1-4f7b-8489-b68536d46c78": "English",
            "5e015b3c-2c9e-41bc-b5e6-a28f768543f0": "Spanish",
            "5fb40389-b060-49dd-900f-bd404d566816": "80 WPM",
            "8280aedc-c8cc-44b9-bd58-3dcab50e39de": "I’m motivated to join Wander because of its innovative approach to travel and technology, which aligns with my passion for both fields.",
            "a163e84b-91a5-44ff-a285-ab205a1750e9": "I thrive in an async culture as it allows me to manage my time effectively and focus on deep work.",
            "bf35a96f-931f-4d8a-b618-7e718f297677": "I have a strong work ethic, characterized by dedication, attention to detail, and a proactive approach to problem-solving.",
            "c147142f-8c78-441b-ba24-4a8653c683ba": "A normal Saturday for me involves outdoor activities like hiking, followed by relaxing with a book or spending time with family.",
            "c26e0111-d15e-4e8c-b6dd-b36aecc4c075": "I’m very comfortable with technology, having worked with various tools and platforms in my career. I’m always eager to learn new technologies.",
            "c4db965d-ffad-433f-8e07-10ee3c259251": "One of my favorite travel experiences was exploring the cultural heritage of Japan, from Tokyo’s bustling streets to Kyoto’s serene temples.",
            "ccb6138c-0581-469d-8f8f-8c6b1d752c2f": "Yes, I thrive in a self-managed environment. I enjoy taking ownership of my work and driving results independently.",
            "d8812f24-b840-40ba-bf41-26daeb3f2a47": "I prefer to keep political discussions out of the workplace to maintain a focus on collaboration and productivity.",
            "fae3370a-2453-4e64-949c-a24dd67e8c38": "My workstation includes a dual-monitor setup, an ergonomic chair, and a quiet space conducive to focused work.",
            "ff1140c1-1e88-46af-b25b-45591e1da15f": "Yes, I’m looking for a full-time position."
        }

        # Create a dummy resume file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(b"Dummy Resume for John Doe")
            dummy_profile["resume"] = temp_file.name

        # Set up Selenium with non-headless browser
        chrome_options = Options()
        chrome_options.headless = False  # Non-headless for visibility
        chrome_options.add_argument("--no-sandbox")  # Avoid permissions issues
        chrome_options.add_argument("--disable-dev-shm-usage")  # For macOS compatibility
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # Open the job application page
        driver.get(request.job_url)

        # Wait for any input field to ensure the form is loaded
        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input, textarea, select"))
            )
        except Exception as e:
            logger.warning(f"Form fields not found after waiting: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to load form fields: {str(e)}")

        # Fill the form fields
        for field_name, field_info in request.fields.items():
            field_type = field_info.get("type", "text")
            required = field_info.get("required", False)
            options = field_info.get("options", [])
            if field_name in dummy_profile and dummy_profile[field_name]:
                try:
                    # Try locating by name first
                    element = None
                    try:
                        element = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.NAME, field_name))
                        )
                    except Exception as e:
                        logger.debug(f"Field {field_name} not found by NAME, trying ID: {str(e)}")
                        # Fallback to ID
                        element = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.ID, field_name))
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