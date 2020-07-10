
# Spamalot Launcher

Lightweight and hackable "search-and-launch" style application and file
launcher, based on PyQt5.

## Features

### Application (*.desktop*) Launcher

Launch *.desktop* files in specified locations by searching for the
application name or executable name. Before searching, it can show a list
of "favorite" apps.

### Open Window Switcher

Switch to open windows by searching for the window title. Before searching,
it shows a list of all windows open on the current desktop.

### Directory Browser

Type a path starting with `/` or `~` to browse through directories in the
filesystem. Before searching, it shows both the "places" bookmarks in
`user-places.xbel` and a "favorites" directory of your choice.

### Command Line

Execute shell commands (no terminal window).

### Calculator

Do math computations using Python's math library, by starting your search
with `=`. It also works with a limited set of Python built-ins like `len()`.
The previous result is stored in the variable `ans`.

For example,

| Input           | Result |
| --------------- | ------ |
| `=1+1`          | `2`    |
| `=3*cos(2*pi)`  | `3.0`  |
| `=len("hello")` | `5`    |

### Symbolic Calculator

Do symbolic math computations using *sympy*, if you have it installed.
Start your search with `==`. Use `x`, `y` and `z` as symbolic variables.

For example,

| Input                             | Result            |
| --------------------------------- | ----------------- |
| `==x+y+z+1`                       |  `x + y + z + 1`  |
| `==simplify(sin(x)**2+cos(x)**2)` | `1`               |

### Dictionary

Start a search with `define` to get the definition from the `dict` command.


## Dependencies

- *Python* 3.6 or newer
- *PyQt5*
- *wmctrl*
- *sympy* (optional—for evaluating symbolic math expressions)


## Configuration

Spamalot Launcher currently has a hard-coded configuration path at
`~/.spamalot_launcher.config.json` and a cache path at
`~/.spamalot_launcher.cache`.

The configuration file format is JSON.

Desktop files and "favorite" locations are stored in the cache. They can be
reloaded by searching for {"clear", "reset", or "erase"} and "cache".
Alternatively, delete the cache file and restart Spamalot Launcher.


## To-Do

- Move configuration and cache files to standard locations (*.config* and
  *.cache*, respectively)
- Internationalization (e.g. for "define" keyword)
- Restore browser bookmark searching functionality
- Make wmctrl optional by disabling window switching functionality if not
  present
