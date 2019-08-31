import logging
from os.path import join, dirname
from dotenv import load_dotenv
from app import App


def get_logger(file_name):
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(file_name)
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    return logger


def main():
    dotenv_path = join(dirname(__file__), '.env')
    load_dotenv(dotenv_path)

    budgetPy = App(get_logger("app.log"))
    budgetPy.run()


if __name__ == "__main__":
    main()
