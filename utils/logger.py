"""Central diagnostics without exception values, SQL parameters or secrets."""
import logging
from logging.handlers import RotatingFileHandler
import traceback
from pathlib import Path


def configure_logging(folder):
    folder=Path(folder); folder.mkdir(parents=True,exist_ok=True)
    handler=RotatingFileHandler(folder/'application.log',maxBytes=2_000_000,backupCount=4,encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    root=logging.getLogger(); root.setLevel(logging.INFO)
    root.addHandler(handler)


def log_exception(context,exc,tb=None):
    frames=traceback.extract_tb(tb or exc.__traceback__)
    location=' -> '.join(f'{Path(f.filename).name}:{f.lineno}:{f.name}' for f in frames)
    logging.error('%s [%s] %s',context,type(exc).__name__,location)


def friendly_error(exc):
    from sqlalchemy.exc import SQLAlchemyError
    from utils.validators import ValidationError
    if isinstance(exc,SQLAlchemyError): return 'Database operation failed. Check the connection and migrations.'
    if isinstance(exc,(ValidationError,PermissionError,ValueError)): return str(exc) or 'Check the entered values.'
    if isinstance(exc,OSError): return 'The file or folder could not be accessed. Check that it is available.'
    return 'An unexpected error occurred. Please try again. Technical details were recorded in the application log.'
