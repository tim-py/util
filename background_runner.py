"""
background_runner.py  Optionally run a script in background

Author: Tim Martin  4/9/2020

Uses os.fork() method to create a child copy that will run the decorated
function or method in the background (redirecting stderr and stdout to files)
and the parent terminates.

Decorate the desired function with the run_in_background function below
to be able to run part or all of a python script in the background.
Useful for doing basic input validation prior to switching to background or
running the entire script in background.
See the doc string for run_in_background for available options.

Script will automatically create 2 files with .out and .err extensions for redirected
stdout and stderr respectively. Files are uniquely named to prevent overwriting.
"""
import os
import sys
import logging
import time

logger = logging.getLogger("background_runner")


def get_file_no(file_handle):
    """
    Get the file number from the file handle by calling the file descriptor. Clear as mud?
    :param file_handle: the file handle object
    :return: int - the file number
    """
    # get the file descriptor function from the file handle
    file_desc = getattr(file_handle, 'fileno', None)
    # Call the file descriptor to get the file number
    file_no = file_desc()
    # Validate file_no
    logger.debug("get_file_no for '{}' value={}, type={}".format(
        file_handle.name,
        file_no,
        type(file_no)
    ))
    if type(file_no) is not int:
        raise ValueError("Failed to get file handle number from {}--expected int, got {}".format(
            file_handle.name,
            type(file_no)
        ))
    return file_no


def run_in_background(**decorator_kwargs):
    """
    Main decorator to run a python function in the background. stdout and stderr will be redicrected to
    unique files. Set logging to at least INFO level to have the location displayed at runtime.
    :param decorator_kwargs:
        log_dir=str     - full path to directory to place .out and .err redirected files. If neither
                          log_dir or hom_subdir, then files will be in users home directory
        home_subdir=str - places logs for redirected stdout and stderr under this subdirectory within
                          the users home directory--overridden by log_dir
        bg=bool, list, or str   - a list of strings that if NOT found in the system ARGV list will
                                  instead run in foreground. This gives capability for command line
                                  options to run in background. omit this list to always run in background.
    :return: decorator
    """
    logger.debug("run_in_background outer decorator")

    def background_decorator(bg_function):
        """
        Inner decorator function to handle decorator arguments and return the wrapper function
        """
        #
        # Get the keyword arguments from the some_bg_function decorator
        log_dir = ""
        home_subdir = ""
        bg_options = []
        for k, v in decorator_kwargs.items():
            if k == "home_subdir":
                home_subdir = str(v).strip().strip(os.path.sep)
            elif k == "bg":
                if type(v) == list:
                    bg_options = [str(s) for s in v]
                else:
                    bg_options = [v, ]
            elif k == "log_dir":
                log_dir = str(v).strip().rstrip(os.path.sep)
            else:
                raise ValueError("Unknown keyword '{}'".format(k))
        #
        # Determine the log directory
        if log_dir:
            pass
        elif home_subdir:
            log_dir = os.path.join(os.environ["HOME"], home_subdir)
        else:
            log_dir = os.environ["HOME"]
        logger.debug("log_dir='{}'".format(log_dir))
        #
        # Determine if background run
        if len(bg_options) < 1:
            logger.debug("no background options specified - background enabled")
            enable_background = True
        else:
            for bg_option in bg_options:
                if bg_option in sys.argv:
                    logger.debug("found '{}' in arguments - background enabled".format(bg_option))
                    enable_background = True
                    break
            else:
                logger.debug("running {} in foreground".format(bg_function.__name__))
                enable_background = False

        def background_wrapper(*args, **kwargs):
            """
            Wrapper function that forks a child process that will then run the decorated function
            in the background
            """
            #
            # If the wrapper determined to not enable background, call the function now and return
            if not enable_background:
                return bg_function(*args, **kwargs)
            #
            # Determine the log file names
            script_name = str(sys.argv[0]).rpartition(os.path.sep)[2].rpartition(".")[0]
            log_file_base = "{}_{}_{}".format(script_name, bg_function.__name__, int(time.time() * 1000))
            error_log = os.path.join(log_dir, log_file_base + ".err")
            output_log = os.path.join(log_dir, log_file_base + ".out")
            #
            # Redirect output
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
                logger.debug("created new directory '{}'".format(log_dir))
            logger.debug("running {} in background".format(bg_function.__name__))
            logger.info("stderr and stout will be directed to {} and {}".format(error_log, output_log))
            #
            # Create a fork (child) process that will survive when parent exits
            newpid = os.fork()
            if newpid == 0:
                # This is the child fork (pid is 0) so run the function
                with open(output_log, "w") as file_out_fh:
                    with open(error_log, "w") as file_err_fh:
                        # determine filno for each
                        stdout_fileno = get_file_no(sys.stdout)
                        stderr_fileno = get_file_no(sys.stderr)
                        out_fileno = get_file_no(file_out_fh)
                        err_fileno = get_file_no(file_err_fh)
                        # flush out and err so we don't miss any pending messages
                        sys.stderr.flush()
                        sys.stdout.flush()
                        # redirect the sys out to the file out
                        os.dup2(out_fileno, stdout_fileno)
                        # redirect the sys err to the file err
                        os.dup2(err_fileno, stderr_fileno)
                        logger.debug("from child: calling function {}".format(bg_function.__name__))
                        bg_function(*args, **kwargs)
            else:
                # If debug is on, wait a few seconds for debug logs from get_file_no function
                if logger.getEffectiveLevel() == logging.DEBUG:
                    time.sleep(5)
                logger.debug("parent process done")
                os._exit(0)

        return background_wrapper

    return background_decorator
