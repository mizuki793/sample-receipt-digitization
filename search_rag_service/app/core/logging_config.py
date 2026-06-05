import os
import logging

def configure_logging():
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    try:
        level = getattr(logging, level_name)
    except Exception:
        level = logging.INFO

    fmt = os.getenv(
        "LOG_FORMAT",
        "%Y-%m-%d %H:%M:%S %(levelname)s [%(name)s] %(message)s",
    )
    datefmt = os.getenv("LOG_DATEFMT", "%Y-%m-%d %H:%M:%S")

    logging.basicConfig(level=level, format=fmt, datefmt=datefmt)

    if not os.getenv("LOG_VERBOSE_LIBS"):
        logging.getLogger("uvicorn.error").setLevel(level)
        logging.getLogger("uvicorn.access").setLevel(level)
        logging.getLogger("httpx").setLevel(logging.WARNING)

    logging.getLogger(__name__).debug("Logging configured", extra={"level": level_name})


def get_logger(name: str | None = None):
    pkg = "search_rag_service"
    logger_name = f"{pkg}.{name}" if name else pkg
    return logging.getLogger(logger_name)


class _ModuleLoggerProxy:
    def __init__(self, pkg_name: str):
        self.pkg_name = pkg_name

    def _resolve_logger(self):
        import inspect
        for frame_info in inspect.stack()[2:]:
            module = frame_info.frame.f_globals.get("__name__")
            if module and not module.startswith(__name__):
                logger_name = f"{self.pkg_name}.{module}"
                return logging.getLogger(logger_name)
        return logging.getLogger(self.pkg_name)

    def __getattr__(self, name: str):
        real_logger = self._resolve_logger()
        return getattr(real_logger, name)


logger = _ModuleLoggerProxy("search_rag_service")
