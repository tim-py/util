#! python -u
import logging
import time
import argparse
from background_runner import run_in_background

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("background_function")


def get_cmd_args():
    parser = argparse.ArgumentParser(description="Example scripts for background_runner")
    parser.add_argument('--debug', action="store_true", required=False)
    return parser.parse_args()


# This is an example of decorating a function to run in the background
# Because the bg_options is omitted, it will always run in background.
# stderr and stdout files will be written to users home
@run_in_background()
def some_bg_function(mess="*no message*"):
    for i in range(30):
        logger.info("Running iteration {}".format(i))
        print("{} iteration={}".format(mess, i))
        time.sleep(1)
    print("done!")


def main():
    # get command line options
    opt = get_cmd_args()
    # set logging to debug if requested
    if opt.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    logger.debug("started with args: {}".format(vars(opt)))
    # Run a function in background
    some_bg_function("hello background")
    print("some_bg_function is done")

if __name__ == '__main__':
    main()
