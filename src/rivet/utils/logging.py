import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from platformdirs import user_log_dir
from rich.logging import RichHandler


def setup_logging(verbose: bool = False):
    log_dir = Path(user_log_dir("rivet", appauthor=False))
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "rivet.log"

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )

    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    )
    file_handler.setFormatter(file_formatter)

    console_handler = RichHandler(
        rich_tracebacks=True, markup=True, show_time=False, show_path=False
    )
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)

    if logger.hasHandlers():
        logger.handlers.clear()

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("docker").setLevel(logging.WARNING)

    return log_file
