from scraper import WebScraper

if __name__ == "__main__":
    this_scraper = WebScraper()
    try:
        start_url = "https://www.idealista.com/venta-viviendas/valencia-valencia/?ordenado-por=fecha-publicacion-desc"
        this_scraper.run(start_url)
        
        if this_scraper.state == 'completed':
            print(f"\nResults {len(this_scraper.publications)}:")
            for pub in this_scraper.publications:
                print(f"ID: {pub.id}")
                print(f"Title: {pub.title}")
                print(f"URL: {pub.url}")
                print("---")
        elif this_scraper.state == 'error':
            print(f"Error occurred: {this_scraper.error_message}")
            
    finally:
        this_scraper.cleanup()

