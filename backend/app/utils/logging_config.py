"""
Logging configuration with daily rotation and 30-day retention.
"""
import glob
import logging
import os
from datetime import datetime, timedelta
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


def setup_logging(log_dir: str = "logs", log_level: str = "INFO"):
    """
    Set up logging with daily rotation and 30-day retention.
    
    Args:
        log_dir: Directory to store log files
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Create logs directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    # Convert string level to logging level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # File handler with daily rotation
    log_file = log_path / "nexus.log"
    file_handler = TimedRotatingFileHandler(
        filename=str(log_file),
        when='midnight',
        interval=1,
        backupCount=30,  # Keep 30 days of logs
        encoding='utf-8'
    )
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(detailed_formatter)
    file_handler.suffix = "%Y-%m-%d"  # Date suffix for rotated files

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(console_formatter)

    # Add handlers to root logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Set levels for third-party libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.ERROR)  # Suppress SQLAlchemy logs
    logging.getLogger("sqlalchemy.engine").setLevel(logging.ERROR)  # Suppress SQL query logs
    logging.getLogger("sqlalchemy.pool").setLevel(logging.ERROR)  # Suppress connection pool logs
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # Clean up old log files (older than 30 days)
    cleanup_old_logs(log_path, days=30)

    logging.info(f"Logging configured - Level: {log_level}, Directory: {log_dir}")
    logging.info(f"Log files will be rotated daily and retained for 30 days")


def cleanup_old_logs(log_dir: Path, days: int = 30):
    """
    Remove log files older than specified days.
    
    Args:
        log_dir: Directory containing log files
        days: Number of days to retain logs
    """
    try:
        cutoff_date = datetime.now() - timedelta(days=days)

        # Find all log files
        log_files = glob.glob(str(log_dir / "nexus.log.*"))

        deleted_count = 0
        for log_file in log_files:
            try:
                # Extract date from filename (nexus.log.2024-01-15)
                file_date_str = log_file.split('.')[-1]
                file_date = datetime.strptime(file_date_str, "%Y-%m-%d")

                if file_date < cutoff_date:
                    os.remove(log_file)
                    deleted_count += 1
                    logging.debug(f"Deleted old log file: {log_file}")
            except (ValueError, OSError) as e:
                logging.warning(f"Error processing log file {log_file}: {e}")

        if deleted_count > 0:
            logging.info(f"Cleaned up {deleted_count} old log file(s) older than {days} days")

    except Exception as e:
        logging.error(f"Error during log cleanup: {e}", exc_info=True)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)
