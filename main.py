"""Run with the project virtual environment: python main.py."""
import logging
from utils.runtime_paths import data_root
from utils.logger import configure_logging, log_exception, friendly_error


def main():
    configure_logging(data_root() / 'logs')
    logging.info('Application starting')
    try:
        import sys
        if "--self-check" in sys.argv:
            from utils.packaging_check import run_check
            run_check()
        else:
            from ui.app import Application
            Application().mainloop()
    except Exception as exc:
        log_exception('Application startup failed',exc)
        # Native Windows message avoids creating a second Tk root on startup failure.
        import os
        if os.name == 'nt':
            import ctypes
            ctypes.windll.user32.MessageBoxW(None,friendly_error(exc),'Unable to start Family Management',16)
        raise SystemExit(1) from None
    finally:
        logging.info('Application stopped')


if __name__ == '__main__':
    from multiprocessing import freeze_support
    freeze_support()
    main()
