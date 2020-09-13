from flask import Flask

import sys
import logging
import json_log_formatter

# Setup JSON handler for logging
formatter = json_log_formatter.JSONFormatter()
json_handler = logging.StreamHandler(stream=sys.stdout)
json_handler.setFormatter(formatter)

# Configure logging settings
log = logging.getLogger("kubseal-webgui")
log.addHandler(json_handler)
log.setLevel(logging.INFO)

# Set flask werkzeug logger to ERROR
flasklogger = logging.getLogger('werkzeug')
flasklogger.addHandler(json_handler)
flasklogger.setLevel(logging.ERROR)