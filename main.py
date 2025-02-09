import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import os
from pathlib import Path
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Create session directory if it doesn't exist and remove previous pages inside the session directory
session_dir = Path("session")
session_dir.mkdir(exist_ok=True)
for file in session_dir.glob("*.html"):
    file.unlink()

page_counter = 0

def save_page(description):
    global page_counter
    page_counter += 1
    page_name = f"{page_counter:02d}_{description}.html"
    with open(session_dir / page_name, "w", encoding='utf-8') as f:
        f.write(driver.page_source)

# https://stackoverflow.com/questions/70485179/runtimeerror-when-using-undetected-chromedriver
driver = uc.Chrome(version_main=131, use_subprocess=True)

# Extract links from a page using a custom selector (CSS or XPath)
# If url is provided, get it, else if HTML is provided, use it
def extract_links(url: str, html: str, selector: str, description: str = "page") -> dict:
    if url:
        driver.get(url)
        input("Press any key after the page is loaded...")
        save_page(description)
    else:
        driver.page_source = html
    
    # Determine if the selector is XPath or CSS
    if selector.startswith('//') or selector.startswith('./'):
        elements = driver.find_elements(By.XPATH, selector)
    else:
        elements = driver.find_elements(By.CSS_SELECTOR, selector)
    
    links = {}
    for element in elements:
        text = element.text.strip()
        href = element.get_attribute('href')
        if text and href:  # Only add if both text and href exist
            links[text] = href
    
    return links

# Extract DOM boxes from a page using a custom selector (CSS or XPath)
# If url is provided, get it, else if HTML is provided, use it
def extract_dom_boxes(url: str, html: str, selector: str, description: str = "page") -> dict:
    if url:
        driver.get(url)
        input("Press any key after the page is loaded, or the popup is closed...")
        # Wait for the elements to be present
        WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.XPATH, selector)))
        save_page(description)
    else:
        driver.page_source = html
    
    # Determine if the selector is XPath or CSS
    if selector.startswith('//') or selector.startswith('./'):
        dom_boxes = driver.find_elements(By.XPATH, selector)
    else:
        dom_boxes = driver.find_elements(By.CSS_SELECTOR, selector)
    
    return dom_boxes

# Extract items from the DOM boxes using a custom selector (CSS or XPath)
# If url is provided, get it, else if HTML is provided, use it
def extract_item_from_dom_boxes(dom_boxes: list, item_selector: str, description: str = "item", get_href: bool = False) -> list:
    items = []

    for dom_box in dom_boxes:
        try:
            # Find elements within the specific dom_box, not the entire page
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

if __name__ == "__main__":
    # Example usage:
    start_url = "https://www.idealista.com/venta-viviendas/valencia-valencia/?ordenado-por=fecha-publicacion-desc"

    # Get the list of DOM boxes of each publication in this page
    publications = extract_dom_boxes(
        url=start_url,
        html=None,
        selector="//article[contains(@class, 'item')]",
        description="publications"
    )
    print("Found publications:", len(publications))

    # Get the titles from the publications
    titles = extract_item_from_dom_boxes(
        dom_boxes=publications,
        item_selector="//div[contains(@class, 'item-info-container')]//a[contains(@class, 'item-link')]",
        description="titles",
        get_href=False
    )
    print("Found titles:", len(titles))
    for title in titles:
        print(title)

    # Get the urls from the publications
    urls = extract_item_from_dom_boxes(
        dom_boxes=publications,
        item_selector="//div[contains(@class, 'item-info-container')]//a[contains(@class, 'item-link')]",
        description="urls",
        get_href=True
    )
    print("Found urls:", len(urls))
    for url in urls:
        print(url)

    driver.quit()

