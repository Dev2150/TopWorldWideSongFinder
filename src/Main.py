from DialogApp import App
import sys
import os
import logging
from datetime import datetime

def setup_logging():
    """Set up logging to file"""
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
    
    # Create logs directory if it doesn't exist
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # Create log filename with timestamp
    log_filename = os.path.join(logs_dir, f'app_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Redirect stdout and stderr to the log file
    sys.stdout = LoggerWriter(logging.info)
    sys.stderr = LoggerWriter(logging.error)
    
    return logging.getLogger('TopWorldWideSongFinder')

class LoggerWriter:
    """Class to redirect stdout and stderr to logger"""
    def __init__(self, level_function):
        self.level_function = level_function
        self.buffer = ''

    def write(self, message):
        self.buffer += message
        if '\n' in message:
            self.level_function(self.buffer.rstrip())
            self.buffer = ''

    def flush(self):
        if self.buffer:
            self.level_function(self.buffer.rstrip())
            self.buffer = ''

if __name__ == '__main__':
    logger = setup_logging()
    logger.info("Application starting...")

    import warnings
    warnings.filterwarnings("ignore")

    try:
        app = App()
        app.mainloop()
    except Exception as e:
        logger.exception(f"Uncaught exception: {str(e)}")

# Removed the following country links:
# https://www.billboard.com/charts/billboard-thailand-top-thai-country-songs/;thailand-thai