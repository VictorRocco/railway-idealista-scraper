import asyncio
import logging
from scraper import WebScraper

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for more verbose output
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    scraper = None
    try:
        logger.debug("Creating WebScraper instance...")
        scraper = await WebScraper.create()
        start_url = "https://www.idealista.com/venta-viviendas/valencia-valencia/?ordenado-por=fecha-publicacion-desc"
        logger.info(f"Starting scraper with URL: {start_url}")
        await scraper.run(start_url)
        
        if scraper.state == 'completed':
            logger.info(f"Scraping completed successfully. Found {len(scraper.publications)} publications.")
            print(f"\nResults {len(scraper.publications)}:")
            for pub in scraper.publications:
                print(f"ID: {pub.id}")
                print(f"Title: {pub.title}")
                print(f"URL: {pub.url}")
                print("---")
        elif scraper.state == 'error':
            logger.error(f"Scraping failed with error: {scraper.error_message}")
            print(f"Error occurred: {scraper.error_message}")
            
    except Exception as e:
        logger.exception("Unexpected error occurred")
        print(f"Unexpected error: {str(e)}")
    finally:
        if scraper:
            logger.debug("Starting cleanup process...")
            try:
                await scraper.cleanup()
                logger.debug("Cleanup completed successfully")
            except Exception as e:
                logger.error(f"Error during cleanup: {str(e)}")

def cleanup_pending_tasks():
    # Get all tasks from the current event loop
    pending = asyncio.all_tasks()
    if not pending:
        return

    logger.debug(f"Cleaning up {len(pending)} pending tasks...")
    
    # Create a task to cancel all pending tasks
    for task in pending:
        if not task.done():
            logger.debug(f"Cancelling task: {task.get_name()}")
            task.cancel()
    
    # Wait for all tasks to be cancelled
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
    logger.debug("All pending tasks have been cancelled")

def run_scraper():
    try:
        # Create new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run the main function
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("Stopped by user")
    except Exception as e:
        logger.exception("Fatal error in main loop")
    finally:
        try:
            # Clean up pending tasks
            cleanup_pending_tasks()
            
            # Close the event loop
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()
            logger.debug("Event loop closed successfully")
        except Exception as e:
            logger.error(f"Error during event loop cleanup: {str(e)}")

if __name__ == "__main__":
    run_scraper()

