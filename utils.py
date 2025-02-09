
global page_counter = 0

# Create session directory if it doesn't exist and remove previous pages inside the session directory
def setup_session():
    global session_dir
    session_dir = Path("session")
    session_dir.mkdir(exist_ok=True)
    for file in session_dir.glob("*.html"):
        file.unlink()

def save_page(description):
    global page_counter
    page_counter += 1
    page_name = f"{page_counter:02d}_{description}.html"
    with open(session_dir / page_name, "w", encoding='utf-8') as f:
        f.write(driver.page_source)