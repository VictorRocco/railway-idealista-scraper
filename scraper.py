import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from transitions import Machine
from typing import Optional, List
from pathlib import Path
from dataclasses import dataclass
import utils  # Add this import at the top

@dataclass
class Publication:
    id: str
    title: str
    url: str
    
    @classmethod
    def from_url(cls, title: str, url: str):
        # Extract ID from URL like "https://www.idealista.com/inmueble/107272725/"
        id = url.split('/')[-2] if url else None
        return cls(id=id, title=title, url=url)

class WebScraper:
    states = ['init', 'loading_page', 'handling_cookies', 'waiting_page_load', 
              'extracting_publications', 'extracting_details', 
              'error', 'completed']
    
    def __init__(self):
        self.driver = uc.Chrome(version_main=131, use_subprocess=True)
        self.publications: List[Publication] = []
        self.current_url: Optional[str] = None
        self.error_message: Optional[str] = None
        
        # Initialize session directory
        self.session_dir = Path("session")
        self.session_dir.mkdir(exist_ok=True)
        for file in self.session_dir.glob("*.html"):
            file.unlink()
        
        self.page_counter = 0
        
        # Initialize the state machine
        self.machine = Machine(
            model=self,
            states=self.states,
            initial='init',
            auto_transitions=False
        )

        # Define transitions
        self.machine.add_transition('load', 'init', 'loading_page')
        self.machine.add_transition('handle_cookies', 'loading_page', 'handling_cookies')
        self.machine.add_transition('wait_load', ['handling_cookies', 'loading_page'], 'waiting_page_load')
        self.machine.add_transition('extract', 'waiting_page_load', 'extracting_publications')
        self.machine.add_transition('get_details', 'extracting_publications', 'extracting_details')
        self.machine.add_transition('finish', 'extracting_details', 'completed')
        self.machine.add_transition('error', '*', 'error')

        # Add callbacks
        self.machine.on_enter_loading_page('on_loading_page')
        self.machine.on_enter_handling_cookies('on_handling_cookies')
        self.machine.on_enter_waiting_page_load('on_waiting_page_load')
        self.machine.on_enter_extracting_publications('on_extracting_publications')
        self.machine.on_enter_extracting_details('on_extracting_details')

    def save_page(self, description):
        self.page_counter += 1
        page_name = f"{self.page_counter:02d}_{description}.html"
        with open(self.session_dir / page_name, "w", encoding='utf-8') as f:
            f.write(self.driver.page_source)

    def extract_dom_boxes(self, url: str = None, html: str = None, selector: str = None, description: str = "page") -> list:
        if url:
            self.driver.get(url)
            utils.random_delay(2, 4)
            WebDriverWait(self.driver, 10).until(EC.presence_of_all_elements_located((By.XPATH, selector)))
            utils.add_random_noise_to_page(self.driver)
            self.save_page(description)
        
        # Determine if the selector is XPath or CSS
        if selector.startswith('//') or selector.startswith('./'):
            dom_boxes = self.driver.find_elements(By.XPATH, selector)
        else:
            dom_boxes = self.driver.find_elements(By.CSS_SELECTOR, selector)
        
        return dom_boxes

    def extract_item_from_dom_boxes(self, dom_boxes: list, item_selector: str, description: str = "item", get_href: bool = False) -> list:
        items = []

        for dom_box in dom_boxes:
            try:
                elements = dom_box.find_elements(By.XPATH, f".{item_selector}")
                
                for element in elements:
                    if get_href:
                        item = element.get_attribute('href')
                    else:
                        item = element.text.strip()
                    items.append(item or "")
            except Exception as e:
                print(f"Error processing element: {e}")
                continue

        return items

    def on_loading_page(self):
        try:
            self.driver.get(self.current_url)
            utils.random_delay(2, 4)  # Add delay after page load
            utils.add_random_noise_to_page(self.driver)
            
            # Check if cookie popup exists
            try:
                cookie_button = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.ID, "didomi-notice-disagree-button"))
                )
                self.handle_cookies()
            except:
                self.wait_load()
        except Exception as e:
            self.error_message = str(e)
            self.error()

    def on_handling_cookies(self):
        try:
            cookie_button = self.driver.find_element(By.ID, "didomi-notice-disagree-button")
            utils.human_like_click(cookie_button, self.driver)  # Use human-like click
            print("Cookie popup rejected")
            self.wait_load()
        except Exception as e:
            self.error_message = f"Error handling cookies: {str(e)}"
            self.error()

    def on_waiting_page_load(self):
        try:
            # Wait for the main content to be present
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//article[contains(@class, 'item')]"))
            )
            utils.random_delay(1, 2)
            utils.add_random_noise_to_page(self.driver)
            print("Page loaded successfully")
            self.save_page("current_page")
            self.extract()
        except Exception as e:
            self.error_message = f"Error waiting for page load: {str(e)}"
            self.error()

    def on_extracting_publications(self):
        try:
            publications = self.extract_dom_boxes(
                url=None,
                html=self.driver.page_source,
                selector="//article[contains(@class, 'item')]",
                description="publications"
            )
            
            titles = self.extract_item_from_dom_boxes(
                dom_boxes=publications,
                item_selector="//div[contains(@class, 'item-info-container')]//a[contains(@class, 'item-link')]",
                get_href=False
            )
            
            urls = self.extract_item_from_dom_boxes(
                dom_boxes=publications,
                item_selector="//div[contains(@class, 'item-info-container')]//a[contains(@class, 'item-link')]",
                get_href=True
            )
            
            for title, url in zip(titles, urls):
                self.publications.append(Publication.from_url(title=title, url=url))
            
            self.get_details()
        except Exception as e:
            self.error_message = str(e)
            self.error()

    def on_extracting_details(self):
        # Implement detailed extraction here
        self.finish()

    def run(self, start_url: str):
        self.current_url = start_url
        self.load()

    def cleanup(self):
        if self.driver:
            self.driver.quit()