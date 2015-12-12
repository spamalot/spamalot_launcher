
-----------------
Spamalot Launcher
-----------------

Lightweight application and file launcher targeted for KDE SC 4 systems.

Features
--------

Application (".desktop") Launcher
    Launch ".desktop" files in specified locations by searching for the
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


To Do
-----
- Make `sympy` optional (currently raises error if not importable)
- Better PEP-8 conformance
- use `logging` instead of `print`
- Reorganize threading code
- Determine if Spamalot Launcher will run on Python 2.6
- Internationalization (e.g. for "define" keyword)
