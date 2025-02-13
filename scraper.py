import nodriver as nd
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from transitions import Machine
from typing import Optional, List
from pathlib import Path
from dataclasses import dataclass
import utils
import asyncio
import random
import logging
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class Publication:
    id: str
    title: str
    url: str
    
    @classmethod
    def from_url(cls, title: str, url: str, base_url: str = "https://www.idealista.com"):
        # Extract ID from URL like "https://www.idealista.com/inmueble/107272725/"
        id = url.split('/')[-2] if url else None
        
        # Make URL absolute if it's relative
        if url and url.startswith('/'):
            url = f"{base_url}{url}"
            
        return cls(id=id, title=title, url=url)

class WebScraper:
    states = ['init', 'loading_page', 'handling_cookies', 'waiting_page_load', 
              'extracting_publications', 'extracting_details', 
              'error', 'completed']
    
    def __init__(self):
        self.browser = None
        self.page = None
        self.publications: List[Publication] = []
        self.current_url: Optional[str] = None
        self.error_message: Optional[str] = None
        
        # Initialize session directory
        self.session_dir = Path("session")
        self.session_dir.mkdir(exist_ok=True)
        for file in self.session_dir.glob("*.html"):
            file.unlink()
        
        self.page_counter = 0
        
        # Initialize the state machine with async callbacks
        self.machine = Machine(
            model=self,
            states=self.states,
            initial='init',
            auto_transitions=False,
            send_event=True
        )
        
        # Define transitions without callbacks - we'll handle them manually
        self.machine.add_transition('load', 'init', 'loading_page')
        self.machine.add_transition('handle_cookies', 'loading_page', 'handling_cookies')
        self.machine.add_transition('wait_load', ['handling_cookies', 'loading_page'], 'waiting_page_load')
        self.machine.add_transition('extract', 'waiting_page_load', 'extracting_publications')
        self.machine.add_transition('get_details', 'extracting_publications', 'extracting_details')
        self.machine.add_transition('finish', 'extracting_details', 'completed')
        self.machine.add_transition('error', '*', 'error')

    @classmethod
    async def create(cls):
        self = cls()
        logger.info("Creating new WebScraper instance")
        # Specify the path to the Chrome executable
        chrome_path = "/usr/bin/google-chrome"  # Update this path if necessary
        # Initialize nodriver with expert mode and specify the executable path
        self.browser = await nd.start(expert=True, browser_executable_path=chrome_path)
        # Open a new page by navigating to a URL
        self.page = await self.browser.get("about:blank")
        logger.debug(f"Available methods on Tab object: {dir(self.page)}")
        # Maximize the browser window using JavaScript
        try:
            await self.page.evaluate("window.moveTo(0, 0); window.resizeTo(screen.width, screen.height);")
        except AttributeError as e:
            logger.error(f"JavaScript execution method not found: {str(e)}")
            self.error_message = str(e)
            self.error()
        return self

    async def save_page(self, description):
        self.page_counter += 1
        page_name = f"{self.page_counter:02d}_{description}.html"
        content = await self.page.get_content()
        with open(self.session_dir / page_name, "w", encoding='utf-8') as f:
            f.write(content)
        logger.debug(f"Saved page content to {page_name}")

    async def extract_elements(self, selector: str):
        try:
            logger.debug(f"Extracting elements with selector: {selector}")
            if selector.startswith('//'):
                # For XPath, use find_all with the full xpath
                elements = await self.page.find_all(selector)
            else:
                # For CSS selectors, use select_all
                elements = await self.page.select_all(selector)
            logger.debug(f"Found {len(elements)} elements")
            return elements
        except Exception as e:
            logger.error(f"Error extracting elements: {str(e)}")
            return []

    async def extract_text_content(self, element):
        """Helper method to extract text content from an element using multiple fallback methods"""
        try:
            # Try different methods to get text content
            methods = [
                ('innerText', lambda e: e.get_property('innerText')),
                ('textContent', lambda e: e.get_property('textContent')),
                ('title', lambda e: e.get_attribute('title')),
                ('aria-label', lambda e: e.get_attribute('aria-label'))
            ]
            
            for method_name, method in methods:
                try:
                    text = await method(element)
                    if text:
                        logger.debug(f"Successfully extracted text using {method_name}: {text}")
                        return text.strip()
                except Exception as e:
                    logger.debug(f"Failed to extract text using {method_name}: {str(e)}")
                    continue
            
            logger.warning("Failed to extract text using all methods")
            return None
            
        except Exception as e:
            logger.error(f"Error in extract_text_content: {str(e)}")
            return None

    async def on_loading_page(self, event):
        try:
            logger.info(f"Loading page: {self.current_url}")
            self.page = await self.browser.get(self.current_url)
            await asyncio.sleep(random.uniform(2, 4))  # Random delay
            
            # Check for cookie popup using find instead of select
            cookie_button = await self.page.find('#didomi-notice-disagree-button')
            if cookie_button:
                self.handle_cookies()
                await self.on_handling_cookies()
            else:
                self.wait_load()
                await self.on_waiting_page_load()
        except Exception as e:
            logger.error(f"Error loading page: {str(e)}")
            self.error_message = str(e)
            self.error()

    async def on_handling_cookies(self):
        try:
            cookie_button = await self.page.find('#didomi-notice-disagree-button')
            if cookie_button:
                await cookie_button.click()
                logger.info("Cookie popup rejected")
                self.wait_load()
                await self.on_waiting_page_load()
            else:
                raise Exception("Cookie button not found")
        except Exception as e:
            logger.error(f"Error handling cookies: {str(e)}")
            self.error_message = f"Error handling cookies: {str(e)}"
            self.error()

    async def on_waiting_page_load(self):
        try:
            # Wait for the main content to be present using a retry approach
            max_retries = 5
            retry_count = 0
            while retry_count < max_retries:
                elements = await self.extract_elements("//article[contains(@class, 'item')]")
                if elements:
                    break
                logger.debug(f"Retry {retry_count + 1}/{max_retries} waiting for articles")
                await asyncio.sleep(random.uniform(1, 2))
                retry_count += 1
            
            if not elements:
                raise Exception("Timeout waiting for articles to appear")
                
            await self.save_page("current_page")
            logger.info("Page loaded successfully")
            self.extract()
            await self.on_extracting_publications()
        except Exception as e:
            logger.error(f"Error waiting for page load: {str(e)}")
            self.error_message = f"Error waiting for page load: {str(e)}"
            self.error()

    async def on_extracting_publications(self):
        try:
            # Read the last saved HTML page content
            html_file = self.session_dir / "01_current_page.html"
            with open(html_file, "r", encoding="utf-8") as f:
                html = f.read()
            
            soup = BeautifulSoup(html, "html.parser")
            # Use a CSS selector to find articles with class 'item'
            articles = soup.select("article.item")
            logger.info(f"Found {len(articles)} publication elements using BeautifulSoup")
            
            base_url = "https://www.idealista.com"
            for idx, article in enumerate(articles, 1):
                try:
                    # Find the first anchor with class 'item-link' inside the article
                    link = article.select_one("a.item-link")
                    if not link:
                        logger.warning(f"No link element found for publication {idx}")
                        continue

                    url = link.get("href")
                    title = link.get("title")
                    if not title:
                        title = link.get_text(strip=True)

                    if not url or not title:
                        logger.warning(f"Incomplete info for publication {idx}")
                        continue

                    self.publications.append(Publication.from_url(title=title, url=url, base_url=base_url))
                    logger.debug(f"Successfully processed publication {idx}: {title}")
                except Exception as e:
                    logger.error(f"Error processing publication {idx}: {str(e)}")
                    continue

            logger.info(f"Successfully extracted {len(self.publications)} publications")
            self.get_details()
            await self.on_extracting_details()
        except Exception as e:
            logger.error(f"Error in publication extraction: {str(e)}")
            self.error_message = str(e)
            self.error()

    async def on_extracting_details(self):
        # Implement detailed extraction here if needed
        self.finish()

    async def run(self, start_url: str):
        self.current_url = start_url
        self.load()
        await self.on_loading_page(None)

    async def cleanup(self):
        if self.browser:
            try:
                logger.info("Starting cleanup")
                # First try to close all pages
                if hasattr(self.browser, 'pages'):
                    logger.debug("Closing browser pages...")
                    try:
                        pages = await self.browser.pages()
                        for page in pages:
                            try:
                                await page.close()
                                logger.debug("Successfully closed a page")
                            except Exception as e:
                                logger.warning(f"Error closing page: {str(e)}")
                    except Exception as e:
                        logger.warning(f"Error getting browser pages: {str(e)}")
                
                # Then try to close the browser context
                logger.debug("Attempting to close browser...")
                if hasattr(self.browser, 'close_browser'):
                    try:
                        await self.browser.close_browser()
                        logger.debug("Browser closed using close_browser()")
                    except Exception as e:
                        logger.warning(f"Error using close_browser(): {str(e)}")
                        if hasattr(self.browser, 'quit'):
                            try:
                                await self.browser.quit()
                                logger.debug("Browser closed using quit()")
                            except Exception as e:
                                logger.warning(f"Error using quit(): {str(e)}")
                elif hasattr(self.browser, 'quit'):
                    try:
                        await self.browser.quit()
                        logger.debug("Browser closed using quit()")
                    except Exception as e:
                        logger.warning(f"Error using quit(): {str(e)}")
                
                self.browser = None
                self.page = None
                logger.info("Cleanup completed successfully")
            except Exception as e:
                logger.error(f"Error during cleanup: {str(e)}", exc_info=True)
                raise  # Re-raise the exception for proper handling in the main function