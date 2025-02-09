import random
import time
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

# Add a random delay between actions
def random_delay(min_seconds: float = 1.0, max_seconds: float = 3.0):
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)

# Simulate human-like mouse movements
def human_like_mouse_move(driver: WebDriver):
    try:
        # Reset mouse position to center of viewport
        viewport_width = driver.execute_script("return window.innerWidth;")
        viewport_height = driver.execute_script("return window.innerHeight;")
        actions = ActionChains(driver)
        actions.move_by_offset(viewport_width//2, viewport_height//2).perform()
        
        # Make 2-4 relative movements from current position
        for _ in range(random.randint(2, 4)):
            # Move relative to current position (-100 to +100 pixels)
            x_offset = random.randint(-100, 100)
            y_offset = random.randint(-100, 100)
            actions = ActionChains(driver)
            actions.move_by_offset(x_offset, y_offset)
            random_delay(0.1, 0.3)
            actions.perform()
        
        random_delay(0.5, 1.0)
    except Exception as e:
        print(f"Warning: Mouse movement failed: {str(e)}")
        # Continue execution even if mouse movement fails

# Simulate a more human-like click with mouse movement
def human_like_click(element: WebElement, driver: WebDriver):
    try:
        actions = ActionChains(driver)
        
        # Move directly to element (safer than offset)
        actions.move_to_element(element)
        random_delay(0.1, 0.3)
        actions.click()
        actions.perform()
        random_delay(0.5, 1.0)
    except Exception as e:
        print(f"Warning: Human-like click failed, falling back to regular click: {str(e)}")
        element.click()  # Fallback to regular click
        random_delay(0.5, 1.0)

# Perform random scrolling on the page
def scroll_randomly(driver: WebDriver):  
    try:
        total_height = driver.execute_script("return document.body.scrollHeight")
        viewport_height = driver.execute_script("return window.innerHeight")
        
        current_position = 0
        max_scrolls = 5  # Limit maximum scrolls to avoid excessive movement
        scroll_count = 0
        
        while current_position < total_height and scroll_count < max_scrolls:
            # Random scroll amount between 100 and 400 pixels
            scroll_amount = random.randint(100, 400)
            current_position = min(current_position + scroll_amount, total_height)
            
            driver.execute_script(f"window.scrollTo(0, {current_position});")
            random_delay(0.5, 1.5)
            
            # Occasionally scroll back up a bit
            if random.random() < 0.2:  # 20% chance
                current_position = max(0, current_position - random.randint(50, 200))
                driver.execute_script(f"window.scrollTo(0, {current_position});")
                random_delay(0.5, 1.0)
            
            scroll_count += 1
    except Exception as e:
        print(f"Warning: Scrolling failed: {str(e)}")
        # Continue execution even if scrolling fails

# Add random mouse movements, scrolls, and delays to simulate human behavior
def add_random_noise_to_page(driver: WebDriver):
    try:
        # Randomly choose which actions to perform
        if random.random() < 0.7:  # 70% chance to move mouse
            human_like_mouse_move(driver)
        if random.random() < 0.8:  # 80% chance to scroll
            scroll_randomly(driver)
        random_delay()
    except Exception as e:
        print(f"Warning: Random noise generation failed: {str(e)}")
        random_delay()  # At least add some delay even if other actions fail