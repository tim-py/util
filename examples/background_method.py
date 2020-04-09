#! python -u
import logging
import time
import argparse
from background_runner import run_in_background

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("background_method")


def get_cmd_args():
    parser = argparse.ArgumentParser(description="Example scripts for background_runner")
    parser.add_argument('--debug', action="store_true", required=False)
    parser.add_argument('--background', action="store_true", required=False)
    return parser.parse_args()


class ScriptRunner:

    def __init__(self, message):
        self.message = message

    # This is an example of decorating a method to run in the background
    # if the --background is provided.  stderr and stdout will be written
    # to files in the 'bg' subdirectory under the user's home
    @run_in_background(bg="--background", home_subdir="bg")
    def some_bg_method(self):
        for i in range(30):
            logger.info("Running class iteration {}".format(i))
            print("{} class iteration={}".format(self.message, i))
            time.sleep(1)
        print("class is done!")

    def validate(self):
        """
        Fake validation meothod
        :return: always True
        """
        logger.info("Validation is good: '{}'".format(self.message))
        return True


def main():
    # get command line options
    opt = get_cmd_args()
    # set logging to debug if requested
    if opt.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    logger.debug("started with args: {}".format(vars(opt)))
    # create a runner object
    runner = ScriptRunner("hello classy background")
    # mock validate
    if not runner.validate():
        raise RuntimeError("Unrecoverable error: failed validation")
    # call the method that may run in background
    runner.some_bg_method()


if __name__ == '__main__':
    main()