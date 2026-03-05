import logging
import sys


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    has_stdout_handler = any(
        isinstance(handler, logging.StreamHandler) and handler.stream is sys.stdout
        for handler in logger.handlers
    )
    if not has_stdout_handler:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(handler)

    logger.propagate = False
    return logger
