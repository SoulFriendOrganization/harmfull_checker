from typing import Optional
import logging
import os
from langchain_openai import AzureChatOpenAI
from langchain.prompts import HumanMessagePromptTemplate, ChatPromptTemplate, SystemMessagePromptTemplate
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pydantic import BaseModel, Field
import tempfile
import asyncio
from playwright.sync_api import sync_playwright
import platform
import subprocess
import sys

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
        self.llm = AzureChatOpenAI(
            deployment_name="gpt-4.1",
            model="gpt-4.1",
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            temperature=0.5,
            max_tokens=5000
        )

    def install_playwright_browsers(self):
        """Run 'playwright install' based on the operating system."""
        try:
            os_name = platform.system()
            command = ["playwright", "install"]
            logger.info(f"Installing Playwright browsers with command: {' '.join(command)}")
            subprocess.run(command, check=True, shell=(os_name == "Windows"))
            logger.info("Playwright browsers installed successfully.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install Playwright browsers: {e}")
            sys.exit(1)

    def get_html_and_images(self, url: str) -> Optional[tuple]:
        try:
            logger.info(f"[WebScraper] Attempting to go URL with Playwright: {url}")
            with sync_playwright() as p:
                browser = None
                try:
                    browser = p.chromium.launch(headless=True)
                except Exception as e:
                    if "Executable doesn't exist" in str(e):
                        logger.warning("Browser executable missing. Attempting to install Playwright browsers...")
                        self.install_playwright_browsers()
                        try:
                            browser = p.chromium.launch(headless=True)
                        except Exception as retry_e:
                            logger.error(f"Failed to launch browser after installation: {retry_e}")
                            return None
                    else:
                        logger.error(f"Unexpected error launching browser: {e}")
                        return None
                page = browser.new_page()
                page.goto(url, timeout=30000)
                page.wait_for_load_state("networkidle", timeout=10000)
                # Get HTML
                content = page.content()
                soup = BeautifulSoup(content, 'html.parser')
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
                    top_screenshot = page.screenshot(type="png")
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight/2);")
                    middle_screenshot = page.screenshot(type="png")
                    import base64
                    images = {
                        "first": f"data:image/png;base64,{base64.b64encode(top_screenshot).decode()}",
                        "second": f"data:image/png;base64,{base64.b64encode(middle_screenshot).decode()}"
                    }
                    logger.info(f"[WebScraper] Successfully captured screenshots for {url}")
                except Exception as img_e:
                    logger.error(f"[WebScraper] Failed to capture screenshots from {url}: {img_e}")
                    images = None
                if body_content is None and images is None:
                    return None
                return (body_content, images)
        except Exception as e:
            logger.error(f"[WebScraper] Failed to scrape {url} with Playwright: {e}")
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