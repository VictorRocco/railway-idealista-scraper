import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from transitions import Machine
from typing import Optional, List
from pathlib import Path
from dataclasses import dataclass

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
    states = ['init', 'loading_page', 'waiting_for_user', 
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
        self.machine.add_transition('wait_input', 'loading_page', 'waiting_for_user')
        self.machine.add_transition('extract', 'waiting_for_user', 'extracting_publications')
        self.machine.add_transition('get_details', 'extracting_publications', 'extracting_details')
        self.machine.add_transition('finish', 'extracting_details', 'completed')
        self.machine.add_transition('error', '*', 'error')

        # Add callbacks
        self.machine.on_enter_loading_page('on_loading_page')
        self.machine.on_enter_waiting_for_user('on_waiting_for_user')
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
            input("Press any key after the page is loaded, or the popup is closed...")
            # Wait for the elements to be present
            WebDriverWait(self.driver, 10).until(EC.presence_of_all_elements_located((By.XPATH, selector)))
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
            self.wait_input()
        except Exception as e:
            self.error_message = str(e)
            self.error()

    def on_waiting_for_user(self):
        try:
            input("Press any key after the page is loaded...")
            self.save_page("current_page")
            self.extract()
        except Exception as e:
            self.error_message = str(e)
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