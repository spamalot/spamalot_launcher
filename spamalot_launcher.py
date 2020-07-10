#!/usr/bin/env python3

# This file is part of Spamalot Launcher.
#
# Spamalot Launcher is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Spamalot Launcher is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Spamalot Launcher.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import division

import sys
import time
import logging

logger = logging.getLogger()
## logger.setLevel(logging.DEBUG)
logging.debug('Logging is enabled.')

import sip
sip.setapi('QString', 2)
sip.setapi('QVariant', 2)

appName = 'launcher.py'
catalog = ''
programName = 'Spamalot Launcher'
version = '2020-06-30'
description = ''
license = 'GPL3'
copyright = '(c) 2020 Spamalot'
text = 'none'
homePage = 'github.com/spamalot/spamalot_launcher'
bugEmail = 'spamalot@users.noreply.github.com'

from PyQt5.QtCore import Qt, QSharedMemory
from PyQt5.QtWidgets import QApplication, QShortcut
from PyQt5.QtGui import QKeySequence

from PyQt5.QtCore import QIODevice, pyqtSignal, QObject, QCoreApplication
from PyQt5.QtNetwork import QLocalServer, QLocalSocket

class Lock(QObject):

    ready = pyqtSignal()
    awoken = pyqtSignal()
    blocked = pyqtSignal()

    def __init__(self, key):
        QObject.__init__(self)
        self._new_sockets = {}
        self._socket_count = 0
        self.key = key

    def apply(self):
        self.socket = QLocalSocket()
        self.socket.connected.connect(self.message_existing)
        self.socket.error.connect(self.start_new_instance)
        self.socket.connectToServer(self.key, QIODevice.WriteOnly)

    def message_existing(self):
        self.socket.write(b'\n')
        self.socket.waitForBytesWritten()  # In case there is no event loop.
        self.socket.disconnectFromServer()
        self.blocked.emit()

    def start_new_instance(self):
        self.server = QLocalServer()
        QCoreApplication.instance().aboutToQuit.connect(self.server.close)
        if self.server.listen(self.key):
            self.server.newConnection.connect(self._listen_message)
            self.ready.emit()
        else:
            self._crash_recover()

    def _crash_recover(self):
        self.server.removeServer(self.key)
        self.start_new_instance()

    def _listen_message(self):
        self._socket_count += 1
        self._new_sockets[self._socket_count] = (
            self.server.nextPendingConnection())
        self._new_sockets[self._socket_count].readyRead.connect(
            functools.partial(self.read_message, self._socket_count))

    def read_message(self, socket_id):
        del self._new_sockets[socket_id]
        self.awoken.emit()


# Delay loading resources until after single-instance check to ensure faster
# start-up times of existing instance.
import subprocess
import os
import os.path
import glob
import re
import pickle
import math
import json
import functools
import xml.etree.ElementTree as ET


from PyQt5.QtCore import Qt, QObject, QEvent, pyqtSignal, QThread, QSize, QUrl
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout,
                         QAbstractItemView, QListWidgetItem,
                          QLineEdit, QListWidget)
from PyQt5.QtGui import  QPalette, QFont, QBrush, QIcon


# NOTE: Use exo-open because it doesn't have this ages old bug:
# https://bugs.launchpad.net/ubuntu/+source/glib2.0/+bug/378783

DEFAULT_CONFIG = '''
{
    "monospace font": "monospace",
    "desktop paths": ["/usr/share/applications",
                      "/usr/local/share/applications",
                      "~/.local/share/applications"],
    "favorite apps": [],
    "favorites directory": "",
    "open command": "exo-open",
    "file manager command": "dolphin",
    "reveal in file manager command": "dolphin --select",
    "icon size": 48,
    "translucent background": true
}
'''
CONFIG_PATH = '~/.spamalot_launcher.config.json'
CACHE_PATH = '~/.spamalot_launcher.cache'
WINDOW_TITLE = 'Spamalot Launcher'

MATH_BUILTINS = ('min', 'max', 'abs', 'hex', 'bin', 'int', 'oct', 'bool')

ItemTypeRole = Qt.UserRole
ItemDataRole = Qt.UserRole + 1


class DictionaryProvider(object):

    def provide(self, search):
        if search.startswith('define ') and search != 'define ':
            item = QListWidgetItem(
                subprocess.check_output('dict {}; exit 0'.format(search[7:]),
                                        stderr=subprocess.STDOUT, shell=True).decode('utf-8'))
            item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
            yield item
            yield True
        yield False


class CalculatorProvider(object):

    def __init__(self):
        self.ans = None
        self.sympy = None

    def sympy_prettify(self, object_):
        return self.sympy.pretty(object_, use_unicode=True)

    def provide(self, search):
        if not search.startswith('='):
            yield False
        if search.startswith('=='):
            if self.sympy is None:
                try:
                    import sympy
                except ImportError:
                    logging.warning('"sympy" not found.')
                    yield QListWidgetItem('"sympy" not found.')
                    yield True
                self.sympy = sympy
            locals_ = {name: getattr(self.sympy, name) for name in
                       (attribute for attribute in dir(self.sympy)
                        if not attribute.startswith('_'))}
            for variable in ('x', 'y', 'z'):
                locals_[variable] = self.sympy.var(variable)
            prettify = self.sympy_prettify
        else:
            locals_ = {name: getattr(math, name) for name in
                       (attribute for attribute in dir(math)
                        if not attribute.startswith('_'))}
            for builtin in MATH_BUILTINS:
                locals_[builtin] = getattr(__builtins__, builtin)
            prettify = str
        try:
            locals_['ans'] = self.ans
            for builtin in (len, str):
                locals_[builtin.__name__] = builtin
            # Not safe in the least, but will prevent honest mistakes
            self.ans = eval(search.lstrip('='), {'__builtins__': None},
                            locals_)
            item = QListWidgetItem(prettify(self.ans))
            # Disabled to allow copy-paste of results
            #item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
            item.setFont(QFont(config_options['monospace font']))
            yield item
        except Exception as err:
            yield QListWidgetItem(str(err))
        yield True


class CommandLineProvider(object):

    def provide(self, search):
        if not search:
            yield False
        try:
            subprocess.check_call(['which', '--', search.split()[0]])
        except subprocess.CalledProcessError:
            pass
        else:
            item = QListWidgetItem(search)
            item.setForeground(Qt.red)
            item.setData(ItemTypeRole, 'executable')
            item.setData(ItemDataRole, search)
            yield item
        yield False



def load_cache(*, provider, generator):
    key = provider.__class__.__name__

    data = {}

    if os.path.isfile(os.path.expanduser(CACHE_PATH)):
        with open(os.path.expanduser(CACHE_PATH), 'rb') as pickle_db:
            data = pickle.load(pickle_db)
        if key in data:
            logging.debug(f'Loading "{key}" cache from file.')
            return data[key]
    else:
        logging.debug('Generating cache file.')

    logging.debug(f'Generating "{key}" cache.')
    data[key] = generator()
    with open(os.path.expanduser(CACHE_PATH), 'wb') as pickle_db:
        pickle.dump(data, pickle_db, protocol=2)
    return data[key]


class ApplicationProvider(object):

    def __init__(self):
        self.app_db = load_cache(provider=self, generator=self._do_walk)

    def _do_walk(self):
        NO_DISPLAY_PATTERN = (
            re.compile(r'^\s*NoDisplay\s*=\s*true\s*$', flags=re.MULTILINE))
        NAME_PATTERN = re.compile(r'^\s*Name\s*=\s*(.*)\s*$', flags=re.MULTILINE)
        ICON_PATTERN = re.compile(r'^\s*Icon\s*=\s*(.*)\s*$', flags=re.MULTILINE)
        EXEC_PATTERN = re.compile(r'^\s*Exec\s*=\s*(.*)\s*$', flags=re.MULTILINE)

        paths = []
        for path_dir in map(os.path.expanduser, config_options['desktop paths']):
            for directory, __, file_names in os.walk(path_dir):
                for file_name in file_names:
                    paths.append(os.path.join(directory, file_name))

        database = []
        for path in paths:
            with open(path) as desktop_file:
                contents = desktop_file.read()
                if NO_DISPLAY_PATTERN.search(contents):
                    continue
                name = NAME_PATTERN.search(contents)
                icon = ICON_PATTERN.search(contents)
                exec_ = EXEC_PATTERN.search(contents)
                database.append({'path': path,
                                'name': name.group(1) if name else '',
                                'icon': icon.group(1) if icon else None,
                                'exec': exec_.group(1) if exec_ else ''
                                })

        return database


    def provide(self, search):
        for app in self.app_db:
            if ((search and (search.lower() in app['name'].lower() or
                             search.lower() in app['exec'].lower())) or
                    (not search and app['name'] in
                        config_options['favorite apps'])):
                item = (QListWidgetItem(QIcon.fromTheme(app['icon'], QIcon(app['icon'])), app['name'])
                        if app['icon'] else QListWidgetItem(app['name']))
                item.setData(ItemTypeRole, 'application')
                item.setData(ItemDataRole, app['path'])
                item.setSizeHint(QSize(1, config_options['icon size'] + 4))
                yield item
        yield False


class DirectoryProvider(object):

    def __init__(self):
        self._user_places_cache = load_cache(
            provider=self, generator=self._generate_user_places_cache)

    def _generate_user_places_cache(self):
        cache = {}
        root = ET.parse('/home/ml/.local/share/user-places.xbel').getroot()
        for bookmark in root.findall('bookmark'):
            only_in_app = bookmark.find('info/metadata/OnlyInApp') is not None
            is_hidden_temp = bookmark.find('info/metadata/IsHidden')
            is_hidden = is_hidden_temp is not None and is_hidden_temp.text != 'false'
            if not only_in_app and not is_hidden:
                path = bookmark.get('href')

                # To enforce the right format for the launching function
                fileprefix = 'file://'
                if path.startswith(fileprefix):
                    path = path[len(fileprefix):]

                title = bookmark.find('title').text

                cache[title] = path
        return cache

    def _ignorecase(self, c):
        if not c.isalpha():
            return c
        return f'[{c.lower()}{c.upper()}]'

    def _item_from_path(self, path, title=None):
        item = QListWidgetItem(path if title is None else title)
        item.setForeground(Qt.blue if title is None else Qt.darkBlue)
        item.setData(ItemTypeRole, 'file')
        item.setData(ItemDataRole, path)
        return item

    def provide(self, search):
        if not search:
            for title in sorted(self._user_places_cache):
                yield self._item_from_path(self._user_places_cache[title], title)

            for path in sorted(glob.glob(os.path.expanduser(os.path.expandvars(
                    config_options['favorites directory'] + '/*')))):
                # Don't bother filtering out files, because it might be useful
                # use case anyway.
                yield self._item_from_path(path)

            yield False

        else:
            if not search.startswith('/') and not search.startswith('~'):
                yield False

            expanded = os.path.expanduser(os.path.expandvars(search+'*'))

            for path in sorted(glob.glob(''.join(map(self._ignorecase, expanded)))):
                if os.path.isdir(path):
                    yield self._item_from_path(path)

            yield True


class OpenWindowProvider(object):

    def __init__(self):
        self._last_time = 0
        self._cache = []
        self._desktop = None
        self._update()

    def _update(self):
        self._last_time = time.time()
        out = subprocess.check_output(['wmctrl', '-l']).decode('utf-8').strip()
        if not out:
            self._cache = []
        else:
            self._cache = [x.split(maxsplit=3) for x in out.split('\n')]

        out2 = subprocess.check_output(['wmctrl', '-d']).decode('utf-8').strip()
        desktops = [x.split() for x in out2.split('\n')]
        try:
            self._desktop = next(x[0] for x in desktops if x[1] == '*')
        except StopIteration:
            # NOTE: Sometimes wmctrl returns that no desktops are active.
            # E.g., this happens in i3 when a new monitor is connected
            # and no windows have been opened on it yet. Since there are
            # no windows in this case, I think this is a fair behaviour.
            self._desktop = None

    def provide(self, search):
        # Refresh if more than 3 seconds stale
        if time.time() - self._last_time > 3:
            self._update()

        for win in self._cache:
            wid = win[0]
            desktop = win[1]
            title = win[3]

            if title == WINDOW_TITLE:
                # Ignore our own window (based on title)
                continue

            if ((not search and desktop == self._desktop) or
                (search and search.lower() in title.lower())):
                item = QListWidgetItem(title)
                item.setForeground(Qt.darkGreen)
                item.setData(ItemTypeRole, 'wid')
                item.setData(ItemDataRole, wid)
                yield item

        yield False


class ResetCacheProvider(object):

    def provide(self, search):
        words = set(search.lower().split())

        if len(words) == 2 and 'cache' in words and (words & {'empty', 'clear', 'reset'}):
            item = QListWidgetItem('RESET CACHE')
            item.setForeground(Qt.magenta)
            item.setData(ItemTypeRole, 'reset_cache')
            yield item
            yield True

        yield False


'''
class BalooDesktopSearchProvider(object):

    def provide(self, search):
        if not search:
            yield False
        baloo_dump = subprocess.check_output(
            ['baloosearch', '-l', '20', '--'] + search.split())#.decode('utf-8')
        # Remove last item because it's the elapsed time.
        paths = baloo_dump.rstrip().split('\n')[:-1]
        for path in paths:
            item = (path,)
            item.setForeground(Qt.blue)
            item.setData(ItemTypeRole, 'file')
            item.setData(ItemDataRole, path)
            yield item
        yield False
'''

'''
class TrackerDesktopSearchProvider(object):

    def provide(self, search):
        if not search:
            yield False
        tracker_dump = subprocess.check_output(
            ['tracker', 'search', '--disable-snippets', '--limit=25', '--'] + search.split())#.decode('utf-8')
        paths = re.findall('\x1b\\[32m(.*)\x1b\\[0m', tracker_dump)
        #print(paths)
        for path in paths:
            path = QUrl(path).toLocalFile()
            #print(path)
            item = (path,)
            item.setForeground(Qt.blue)
            item.setData(ItemTypeRole, 'file')
            item.setData(ItemDataRole, path)
            yield item
        yield False
'''

'''
class LocateProvider(object):

    def provide(self, search):
        if len(search) < 3:
            yield False
        locate_dump = subprocess.check_output(
            ['locate', '-i', '--', search])#.decode('utf-8')
        paths = locate_dump.split('\n')
        for path in paths:
            item = (path,)
            item.setForeground(Qt.blue)
            item.setData(ItemTypeRole, 'file')
            item.setData(ItemDataRole, path)
            yield item
        yield False
'''

'''
class ChromeBookmarkProvider(object):

    def __init__(self):
        self.bookmarks = []
        try:
            with open(os.path.expanduser(config_options['chrome path'])) as desktop_file:
                contents = desktop_file.read()
        except IOError:
            logging.warn('Cannot find Chrome bookmarks file.')
            return
        contents = json.loads(contents)
        self.populate(contents['roots']['bookmark_bar']['children'])

    def populate(self, items):
        for item in items:
            if item['type'] == 'folder':
                self.populate(item['children'])
            elif item['type'] == 'url':
                self.bookmarks.append({'title': item['name'], 'url': item['url']})

    def provide(self, search):
        if not search:
            yield False
        for bookmark in self.bookmarks:
            if search.lower() not in bookmark['title'].lower() and search.lower() not in bookmark['url'].lower():
                continue
            item = (bookmark['title'],)
            item.setForeground(Qt.red)
            item.setData(ItemTypeRole, 'url')
            item.setData(ItemDataRole, bookmark['url'])
            yield item
        yield False
'''

def items_from_search(providers, search):
    items = []
    for provider in providers:
        for result in provider.provide(search.strip()):
            if isinstance(result, QListWidgetItem):
                items.append(result)
            else:
                if result:
                    return items
                break
    return items


class SearchWorker(QObject):

    finished = pyqtSignal()
    new_items = pyqtSignal(list)

    def __init__(self, providers, text, start_time):
        QObject.__init__(self)
        self.providers = providers
        self.text = text
        self.time = start_time
        self.canceled = False

    def process(self):
        if not self.canceled:
            self.new_items.emit(items_from_search(self.providers, self.text))
        self.finished.emit()


class Searcher(object):

    def __init__(self):
        self._last_worker_time = 0
        self._threads = []
        self.workers = []
        self.providers = ()

    def repopulate(self, worker, items):
        # Ensure that a slow-to-execute previous search doesn't override
        # existing search results.
        if worker.time < self._last_worker_time:
            return
        self._last_worker_time = worker.time

        old_workers = self.workers[:self.workers.index(worker)]
        for worker in old_workers:
            worker.canceled = True

        result_list_widget.clear()
        for item in items:
            result_list_widget.addItem(item)

        # Change search bar color to show that search is still loading.
        search_bar.setPalette(main_window.palette())

    def search(self, text):
        logging.debug('Doing search.')
        thread = QThread()

        worker = SearchWorker(self.providers, text, time.time())
        worker.moveToThread(thread)

        def on_worker_finished():
            thread.quit()
            thread.wait()
            worker.deleteLater()

        thread.started.connect(worker.process)
        worker.finished.connect(on_worker_finished)
        worker.new_items.connect(functools.partial(self.repopulate, worker))
        thread.finished.connect(thread.deleteLater)

        self._threads.append(thread)
        self.workers.append(worker)
        thread.start()

        # Revert search bar color.
        palette = main_window.palette()
        brush = palette.brush(QPalette.Highlight).color()
        palette.setBrush(QPalette.Base, QBrush(brush))
        search_bar.setPalette(palette)

        # Clean up old threads.
        self._threads = [thread for thread in self._threads
                         if not sip.isdeleted(thread)]
        self.workers = [worker for worker in self.workers
                        if not sip.isdeleted(worker)]


def launch_item(item):
    if item is None:
        logging.warning('Nothing to open!')
        return

    if item.data(ItemTypeRole) == 'application':
        subprocess.Popen(config_options['open command'].split() + [item.data(ItemDataRole)])
    elif item.data(ItemTypeRole) == 'file':
        if os.path.isdir(item.data(ItemDataRole)):
            # Open folders as-is.
            subprocess.Popen(config_options['file manager command'].split() + [item.data(ItemDataRole)])
        else:
            # Select files without opening their respective program.
            subprocess.Popen(config_options['reveal in file manager command'].split() + [item.data(ItemDataRole)])
    elif item.data(ItemTypeRole) == 'url':
        subprocess.Popen(['x-www-browser', item.data(ItemDataRole)])
    elif item.data(ItemTypeRole) == 'executable':
        subprocess.Popen(item.data(ItemDataRole), shell=True)
    elif item.data(ItemTypeRole) == 'wid':
        wid = item.data(ItemDataRole)
        subprocess.Popen(['wmctrl', '-i', '-a', item.data(ItemDataRole)])
    elif item.data(ItemTypeRole) == 'reset_cache':
        clear_cache()
        return
    else:
        logging.warning('This item cannot be opened.')
        return
    close()


def launch_active_item():
    item = result_list_widget.item(0)
    if result_list_widget.currentItem() is not None:
        item = result_list_widget.currentItem()
    result_list_widget.itemActivated.emit(item)


def autofill_search(item, previous):
    if item is None:
        return
    if item.data(ItemTypeRole) == 'file':
        search_bar.setText(item.text())


def clear_search():
    search_bar.clear()
    # Need to call manually because we're using textEdited below
    search_bar.textEdited.emit('')


def close():
    clear_search()
    main_window.hide()


def clear_cache():
    os.remove(os.path.expanduser(CACHE_PATH))
    reload_config()
    logging.debug('Cache cleared!')
    searcher.providers = make_providers()
    clear_search()


def reload_config():
    global config_options
    if not os.path.exists(os.path.expanduser(CONFIG_PATH)):
        with open(os.path.expanduser(CONFIG_PATH), 'w') as f:
            f.write(DEFAULT_CONFIG)
    try:
        with open(os.path.expanduser(CONFIG_PATH)) as f:
            config_options = json.loads(f.read())
    except Exception as err:
        logging.error(str(err))
        logging.warning('Using default configuration options.')
        config_options = json.loads(DEFAULT_CONFIG)

    # Apply GUI config
    if config_options['translucent background']:
        main_window.setAttribute(Qt.WA_TranslucentBackground)
    result_list_widget.setIconSize(QSize(*(config_options['icon size'],) * 2))


def make_providers():
    # TODO: should make configurable with config file
    return (ResetCacheProvider(),
             DictionaryProvider(), CalculatorProvider(), DirectoryProvider(),
             OpenWindowProvider(), CommandLineProvider(),ApplicationProvider())


class KeyBindingEventFilter(QObject):

    """Event filter to quit Qt application when escape is pressed."""

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Escape:
                close()
                return True
            if event.key() == Qt.Key_Down and search_bar.hasFocus():
                result_list_widget.setCurrentRow(result_list_widget.currentRow() + 1)
                return True
            if event.key() == Qt.Key_Up and search_bar.hasFocus():
                result_list_widget.setCurrentRow(result_list_widget.currentRow() - 1)
                return True
        return False





app = QApplication(sys.argv)

def on_launch(*, first_instance):
    if first_instance:
        app.setQuitOnLastWindowClosed(False)
    else:
        if main_window.isVisible():
            close()
        else:
            main_window.show()
            search_bar.setFocus(True)
    return 0


x = Lock('spamalot_launcher')
x.ready.connect(lambda: on_launch(first_instance=True))
x.blocked.connect(lambda: sys.exit(0))
x.awoken.connect(lambda: on_launch(first_instance=False))
x.apply()

main_window = QWidget()

shortcut = QShortcut(QKeySequence(Qt.CTRL + Qt.Key_Q), main_window)
shortcut.activated.connect(QApplication.quit)

main_window.setWindowTitle(WINDOW_TITLE)

main_window.setWindowFlags(Qt.FramelessWindowHint)
main_window.show()

layout = QVBoxLayout(main_window)

search_bar = QLineEdit()
search_bar.returnPressed.connect(launch_active_item)

layout.addWidget(search_bar)

result_list_widget = QListWidget()

result_list_widget.setAlternatingRowColors(True)
result_list_widget.setTextElideMode(Qt.ElideMiddle)
result_list_widget.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
result_list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
result_list_widget.currentItemChanged.connect(autofill_search)
result_list_widget.itemActivated.connect(launch_item)

# Prepare alternating row colors for transparency
palette = result_list_widget.palette()
color = palette.brush(QPalette.Base).color()
color.setAlphaF(0.9)
palette.setBrush(QPalette.Base, QBrush(color))
color = palette.brush(QPalette.AlternateBase).color()
color.setAlphaF(0.5)
palette.setBrush(QPalette.AlternateBase, QBrush(color))
main_window.setPalette(palette)

layout.addWidget(result_list_widget)
main_window.installEventFilter(KeyBindingEventFilter(main_window))

reload_config()

searcher = Searcher()
searcher.providers = make_providers()
searcher.search('')  # Populate with favorite applications.
# Not using text changed to allow for programmatic updates via selection changes
search_bar.textEdited.connect(searcher.search)

sys.exit(app.exec_())
