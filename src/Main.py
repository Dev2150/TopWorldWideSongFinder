from DialogApp import App
import sys
import os
import logging
import warnings
from datetime import datetime

def setup_logging():
    """Set up logging to file""" # Revert description as we are not redirecting stdout/stderr here
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')

    # Create logs directory if it doesn't exist
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    # Create log filename with timestamp
    log_filename = os.path.join(logs_dir, f'app_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')

    # --- Configure Logging Manually (more control than basicConfig) ---
    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO) # Set the minimum level for the logger

    # Clear existing handlers to avoid duplicates if setup is called multiple times
    # or if default handlers exist (e.g., from previous basicConfig calls)
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # Create File Handler
    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(logging.INFO) # Set minimum level for file output

    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Add formatter to handlers
    file_handler.setFormatter(formatter)

    # Add handlers to the root logger
    root_logger.addHandler(file_handler)
    # -----------------------------------------------------------------

    # Remove stdout and stderr redirection
    # --- Redirect stdout and stderr AFTER handlers are set up ---
    # This captures print() calls etc. and sends them *to* the logger
    # Pass the logger's methods (root_logger.info/error) to LoggerWriter
    # sys.stdout = LoggerWriter(root_logger.info)
    # sys.stderr = LoggerWriter(root_logger.error)
    # ----------------------------------------------------------

    # Return a specific logger for the application's use
    return logging.getLogger('TopWorldWideSongFinder')

# Remove LoggerWriter class definition
# class LoggerWriter:
#     """Class to redirect stdout and stderr to logger"""
#     def __init__(self, level_function):
#         self.level_function = level_function
#         self.buffer = ''
#
#     def write(self, message):
#         message = str(message)
#         self.buffer += message
#         while '\n' in self.buffer:
#             line, self.buffer = self.buffer.split('\n', 1)
#             # Log the complete line, stripping trailing whitespace (including newline)
#             self.level_function(line.rstrip())
#
#     def flush(self):
#         if self.buffer:
#             self.level_function(self.buffer.rstrip())
#             self.buffer = ''

if __name__ == '__main__':
    logger = setup_logging()
    logger.info("Application starting...")

    warnings.filterwarnings("ignore")

    try:
        app = App()
        app.mainloop()
    except Exception as e:
        logger.exception(f"Uncaught exception: {str(e)}")
    logger.info("Application finished.")
# Removed the following country links:
# https://www.billboard.com/charts/billboard-thailand-top-thai-country-songs/;thailand-thai