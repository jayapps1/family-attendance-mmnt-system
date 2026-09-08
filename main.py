"""Run with the project virtual environment: python main.py."""
import logging
from config.settings import BASE_DIR


def main():
    log_folder = BASE_DIR / "logs"
    log_folder.mkdir(exist_ok=True)
    logging.basicConfig(filename=log_folder / "application.log", level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    from ui.app import Application
    Application().mainloop()


if __name__ == "__main__":
    main()
