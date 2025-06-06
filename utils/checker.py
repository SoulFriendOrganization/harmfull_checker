from seleniumbase import Driver
from typing import Optional
import logging
import os
from langchain_openai import AzureChatOpenAI
from langchain.prompts import HumanMessagePromptTemplate, ChatPromptTemplate, SystemMessagePromptTemplate
from time import sleep
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv(override=True)

def setup_logging(log_file='app.log'):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        encoding='utf-8'
    )
    return logging.getLogger("AppLogger")

logger = setup_logging()
class HarmfulCheckerConfig(BaseModel):
    is_harmful: bool = Field(description="Indicates if the content is harmful (like online gambling or phising) or not.")
    summary_harmful: str = Field(description="Summary of the harmful content (hoax, phising, not safety, online gambling, pirating, virus) detected.")


class HarmfulChecker:
    def __init__(self):
        self.llm =  AzureChatOpenAI(
            deployment_name="gpt-4.1",
            model="gpt-4.1",
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            temperature=0.5,
            max_tokens=5000
        )

    def get_html_and_images(self, url: str) -> Optional[tuple]:
        try:
            logger.info(f"[WebScraper] Attempting to go URL with SeleniumBase: {url}")
            driver = Driver(headless=True, ad_block=True, uc=True)
            driver.uc_open_with_reconnect(url, reconnect_time=6)
            try:
                driver.uc_gui_click_captcha()
            except Exception as captcha_e:
                logger.warning(f"[WebScraper] CAPTCHA bypass failed for {url}: {captcha_e}")
            sleep(2)
            # Get HTML
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            body = soup.body
            if not body:
                logger.warning(f"[WebScraper] No <body> tag found in: {url}")
                body_content = None
            else:
                body_content = str(body)
                if not body_content.strip():
                    logger.warning(f"[WebScraper] No content extracted from <body> of: {url}")
                    body_content = None
                else:
                    body_content = f"url: {url}\n{body_content}"
                    logger.info(f"[WebScraper] Successfully extracted HTML from <body> of: {url} (length: {len(body_content)} characters)")
            # Get images
            try:
                top_screenshot = driver.get_screenshot_as_base64()
                scroll_height = driver.execute_script("return document.body.scrollHeight")
                middle_position = scroll_height // 2
                driver.execute_script(f"window.scrollTo(0, {middle_position});")
                sleep(1)
                middle_screenshot = driver.get_screenshot_as_base64()
                images = {
                    "first": f"data:image/png;base64,{top_screenshot}",
                    "second": f"data:image/png;base64,{middle_screenshot}"
                }
                logger.info(f"[WebScraper] Successfully captured screenshots for {url}")
            except Exception as img_e:
                logger.error(f"[WebScraper] Failed to capture screenshots from {url}: {img_e}")
                images = None
            driver.quit()
            if body_content is None and images is None:
                return None
            return (body_content, images)
        except Exception as e:
            if isinstance(e, ProcessLookupError):
                raise
            logger.error(f"[WebScraper] Failed to scrape {url} with SeleniumBase: {e}")
            return None
        
    def harmful_checker(self, url) -> Optional[HarmfulCheckerConfig]:
        try:
            logger.info(f"[HarmfulChecker] Checking URL: {url}")
            content = self.get_html_and_images(url)
            if not content:
                logger.warning(f"[HarmfulChecker] No content found for {url}. Skipping harmful check.")
                return None
            
            body_content, images = content
            if not body_content and not images:
                logger.warning(f"[HarmfulChecker] No HTML content found and no image for {url}. Skipping harmful check.")
                return None
            
            if body_content:
                soup = BeautifulSoup(body_content, "html.parser")
                text_content = soup.get_text(separator=" ", strip=True)
                text_content = text_content.replace("{", "").replace("}", "")
                body_content = text_content
            else:
                body_content = "No HTML content available."
            
            system_prompt = SystemMessagePromptTemplate.from_template(
                template="""You are a helpful assistant that detects harmful content in URLs.
                         You will be provided with HTML content and images from the URL. 
                         Your task is to determine if the content is harmful (like online gambling or phishing) or not, 
                         and provide a summary of the harmful content detected."""
            )
            prompt_template = HumanMessagePromptTemplate.from_template(
                template=[
                    {
                        "type": "image_url",
                        "image_url": images.get("first", ""),
                    },
                    {
                        "type": "image_url",
                        "image_url": images.get("second", ""),
                    },
                    {
                        "type": "text",
                        "text": body_content if body_content else "No HTML content available."
                    }
                ]
            )
            prompt = ChatPromptTemplate.from_messages([system_prompt, prompt_template])
            chain = prompt | self.llm.with_structured_output(HarmfulCheckerConfig)
            logger.info(f"[HarmfulChecker] Running harmful content check for {url}")
            result = chain.invoke({"text": body_content, "images": images})
            if result.is_harmful:
                logger.info(f"[HarmfulChecker] Harmful content detected in {url}: {result.summary_harmful}")
            else:
                logger.info(f"[HarmfulChecker] No harmful content detected in {url}.")
            return result
        except Exception as e:
            logger.error(f"[HarmfulChecker] Error checking URL {url}: {e}")
            return None
        
harmful_checker = HarmfulChecker()