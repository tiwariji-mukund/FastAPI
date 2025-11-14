import logging
import json
import contextvars
import os
from datetime import datetime
from pathlib import Path
import pytz

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar('request_id', default='')

def get_request_id():
    """Get the current request ID from context."""
    return request_id_var.get('')

def set_request_id(request_id: str):
    """Set the request ID in context."""
    request_id_var.set(request_id)

class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs logs in JSON format."""
    
    def format(self, record):
        ist = pytz.timezone("Asia/Kolkata")
        utc_timestamp = datetime.fromtimestamp(record.created, tz=pytz.UTC)
        timestamp = utc_timestamp.astimezone(ist)
        milliseconds = timestamp.microsecond // 10000
        ts_str = timestamp.strftime("%Y-%m-%d %H:%M:%S") + f",{milliseconds:02d}"
        
        workspace_root = Path(__file__).parent.parent.absolute()
        file_path = Path(record.pathname).absolute()
        
        try:
            relative_path = file_path.relative_to(workspace_root)
            caller_path = str(relative_path).replace('\\', '/')
            if not caller_path.startswith('fastapi/'):
                caller_path = f"fastapi/{caller_path}"
        except ValueError:
            caller_path = f"fastapi/{Path(record.pathname).name}"
        
        caller = f"{caller_path}:{record.lineno}"
        
        log_entry = {
            "ts": ts_str,
            "level": record.levelname,
            "caller": caller,
            "msg": record.getMessage()
        }
        
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        if getattr(record, 'include_request_id', False):
            request_id = get_request_id()
            if request_id:
                log_entry["requestId"] = request_id
        
        return json.dumps(log_entry)

class CustomLogger:
    """Custom logger wrapper that provides Info, Error, Infow, and Errorw methods."""
    
    def __init__(self, logger: logging.Logger):
        self._logger = logger
    
    def Info(self, msg: str):
        """Log info message without requestId."""
        self._logger.info(msg, stacklevel=2)
    
    def Error(self, msg: str):
        """Log error message without requestId."""
        self._logger.error(msg, stacklevel=2)
    
    def Infow(self, msg: str, *keys_and_values):
        """Log info message with requestId and additional key-value pairs.
        
        Similar to Go's log.Infow(msg, key1, value1, key2, value2, ...)
        
        Args:
            msg: The log message
            *keys_and_values: Alternating key-value pairs (key1, value1, key2, value2, ...)
        """
        extra_fields = self._parse_keys_and_values(keys_and_values)
        
        extra = {
            'include_request_id': True,
            'extra_fields': extra_fields
        }
        self._logger.info(msg, extra=extra, stacklevel=2)
    
    def Errorw(self, msg: str, *keys_and_values):
        """Log error message with requestId and additional key-value pairs.
        
        Similar to Go's log.Errorw(msg, key1, value1, key2, value2, ...)
        
        Args:
            msg: The log message
            *keys_and_values: Alternating key-value pairs (key1, value1, key2, value2, ...)
        """
        extra_fields = self._parse_keys_and_values(keys_and_values)
        
        extra = {
            'include_request_id': True,
            'extra_fields': extra_fields
        }
        self._logger.error(msg, extra=extra, stacklevel=2)
    
    def _parse_keys_and_values(self, keys_and_values):
        """Parse alternating key-value pairs into a dictionary.
        
        Args:
            keys_and_values: Tuple of alternating keys and values
            
        Returns:
            Dictionary of key-value pairs
            
        Raises:
            ValueError: If number of arguments is odd (missing value for a key)
        """
        if len(keys_and_values) == 0:
            return {}
        
        if len(keys_and_values) % 2 != 0:
            raise ValueError(f"Infow/Errorw expects even number of key-value arguments, got {len(keys_and_values)}")
        
        result = {}
        for i in range(0, len(keys_and_values), 2):
            key = str(keys_and_values[i])
            value = keys_and_values[i + 1]
            result[key] = value
        
        return result
    
    def debug(self, msg: str):
        self._logger.debug(msg)
    
    def warning(self, msg: str):
        self._logger.warning(msg)
    
    def critical(self, msg: str):
        self._logger.critical(msg)

def setup_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    logger.handlers.clear()
    
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    
    logger.propagate = False
    
    return CustomLogger(logger)