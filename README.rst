
-----------------
Spamalot Launcher
-----------------

Lightweight application and file launcher targeted for KDE SC 4 systems.

Features
--------

Application (*.desktop*) Launcher
    Launch *.desktop* files in specified locations by searching for the
    application name or for the binary file name.

Command Line
    Execute shell commands (no terminal window).

Calculator
    Do math computations using Python's math library by starting your search
    with "=".

    For example,

    ============  =======
    Input         Result
    ============  =======
    =1+1          ``2``
    =3*cos(2*pi)  ``3.0``
    ============  =======

Symbolic Calculator
    Do symbolic math computations using `sympy`, if you have it installed.
    Start your search with "==". Use *x*, *y* and *z* as symbolic variables.

    For example,

    ===============================  =================
    Input                            Result
    ===============================  =================
    =x+y+z+1                         ``x + y + z + 1``
    ==simplify(sin(x)**2+cos(x)**2)  ``1``
    ===============================  =================

Dictionary
    Get output from the ``dict`` program by starting your search with "define".


Dependencies
------------
- Python 2.7 or 3.x
- PyKDE4
- PyQt4
- sympy (optional -- for evaluating symbolic math expressions)


Configuration
-------------
Spamalot Launcher currently has a hard-coded configuration path at
'~/.spamalot_launcher.config.json' and a cache path at
'~/.spamalot_launcher.cache'.

The configuration file format is JSON.

Spamalot Launcher will not detect new *.desktop* files unless the cache file
is not found. If a new application is installed and you would like to have it
in the application list, delete the cache file and restart Spamalot Launcher.


To Do
-----
- Use `logging` instead of `print`
- Automatically detect the presence of new *.desktop* files and add them to the
  cache
- Move configuration and cache files to standard locations (*.config* and
  *.cache*, respectively)
- Clean up main-program code
- Determine if Spamalot Launcher will run on Python 2.6
- Internationalization (e.g. for "define" keyword)
