# Python Utility Modules
Collection of utility modules written in Python 3.7

## background_runner.py
A module that provides a decorator to move the script to the background
when the decorated function or method is called.  Both stderr and stdout
are redirected to files in the user's home directory if and when the script
is moved to the background.  Decorator arguments allow for the script's 
command line arguments to control whether it is run in background and provide
a subdirectory for log files.

This method also provides for validation to take place prior to moving to
background

Examples can be found in the examples folder.

To run a function or method always in background and save files to user's home:
> @run_in_background()
> def my_bg_function(args, ...)

To run a function or method only if --bg or -b script arguments and save logs
to ${HOME}/bg:
> @run_in_background(bg=["--bg", "-b"], home_subdir="bg")
> def my_bg_function(args, ...)

Moving to background is accomplished by using the os.fork() mehtod to create
a child copy which redirects stderr and stdout, then the parent process will
exit.

