import logging

import colorlog


LOG_FORMAT = (
    "%(asctime)s | %(log_color)s%(levelname)-7s%(reset)s | %(name)s | "
    "%(filename)s:%(lineno)d | %(funcName)s | %(message)s"
)


def setup_logging(level: str) -> None:
    handler = colorlog.StreamHandler()
    handler.setFormatter(
        colorlog.ColoredFormatter(
            LOG_FORMAT,
            log_colors={
                "DEBUG": "bold_cyan",
                "INFO": "bold_green",
                "WARNING": "bold_yellow",
                "ERROR": "bold_red",
            },
        )
    )

    root = logging.getLogger()
    root.setLevel(level.upper())
    root.handlers.clear()
    root.addHandler(handler)
