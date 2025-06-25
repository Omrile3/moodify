import logging
import json

class StructuredFormatter(logging.Formatter):
    def format(self, record):
        # Keep the basic message format
        record.base_message = super().format(record)
        
        # Handle the extra data if it exists
        if hasattr(record, 'data'):
            try:
                # Format the extra data as JSON
                extra_data = json.dumps(record.data, default=str)
                return f"{record.base_message} - Data: {extra_data}"
            except Exception:
                return record.base_message
        return record.base_message

def setup_logging():
    # Remove any existing handlers
    root = logging.getLogger()
    if root.handlers:
        for handler in root.handlers:
            root.removeHandler(handler)
            
    # Configure the basic logging format
    formatter = StructuredFormatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    )
    
    # Add a single handler with our custom formatter
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    
    # Configure the root logger
    root.addHandler(handler)
    root.setLevel(logging.INFO)
