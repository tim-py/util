# Python Utility Modules
Collection of utility modules written in Python 3.7

## background_runner.py
Traditionally, in order to run a long job in the background and have it 
continue after disconnecting from the shell, the user would have to enter commands
like: 
>nohup long_running_job.py 2>std_err >std_out &

If there was a catostrophic failure during initial validation, the output files
would then need to be checked.  Also, the end-user has to remember the nohup
and & and make sure to redirect it to a file that might get overwritten on a
subsequent run.

This module allows for a python script to be forked into the background by
simply decorating the function call to trigger it.  Backgrounding can be optional
by command line argument or fixed.  It can first perform initial validation and then
background, or background right away. Both stderr and stdout
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

