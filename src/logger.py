import logging
import sqlite3
from datetime import datetime
from typing import Optional

from .datastore import SQLiteDataStore
from .utils import to_milliseconds

class DatabaseHandler(logging.Handler):
    """
    A custom logging handler that writes log records to an SQLite database.
    """
    def __init__(self, db_path: str):
        super().__init__()
        self.db_store = SQLiteDataStore(db_path)
        self.db_store.initialize()

    def emit(self, record: logging.LogRecord):
        """
        Saves a log record to the database.
        """
        now = datetime.now()
        self.db_store.insert_log(
            timestamp_ms=to_milliseconds(now),
            level=record.levelname,
            module=record.name,
            message=record.getMessage()
        )

_logger: Optional[logging.Logger] = None

def get_logger(name: str, db_path: str = "data/trading.db") -> logging.Logger:
    """
    Configures and returns a logger that writes to the console and a database.
    """
    global _logger
    if _logger is None:
        _logger = logging.getLogger("CryptoTrader")
        _logger.setLevel(logging.INFO)
        
        # Prevent logs from being propagated to the root logger
        _logger.propagate = False

        # Console handler
        if not any(isinstance(h, logging.StreamHandler) for h in _logger.handlers):
            console_handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            console_handler.setFormatter(formatter)
            _logger.addHandler(console_handler)

        # Database handler
        if not any(isinstance(h, DatabaseHandler) for h in _logger.handlers):
            db_handler = DatabaseHandler(db_path)
            _logger.addHandler(db_handler)

    return logging.getLogger(name)
