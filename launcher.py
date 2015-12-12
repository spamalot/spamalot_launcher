#!/usr/bin/env python

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
logger.setLevel(logging.DEBUG)
logging.debug('Logging is enabled.')

import sip
sip.setapi('QString', 2)
sip.setapi('QVariant', 2)

from PyKDE4.kdecore import KCmdLineArgs, KCmdLineOptions, ki18n, KAboutData
from PyKDE4.kdeui import KIcon, KUniqueApplication

appName = 'launcher.py'
catalog = ''
programName = ki18n('Spamalot Launcher')
version = '1.0'
description = ki18n('')
license = KAboutData.License_GPL_V3
copyright = ki18n('(c) 2007 Spamalot')
text = ki18n('none')
homePage = 'github.com/spamalot/spamalot_launcher'
bugEmail = 'spamalot@users.noreply.github.com'

aboutData = KAboutData(appName, catalog, programName, version, description,
                       license, copyright, text, homePage, bugEmail)

KCmdLineArgs.init(sys.argv, aboutData)
options = KCmdLineOptions()
KCmdLineArgs.addCmdLineOptions(options)
KUniqueApplication.addCmdLineOptions()

if not KUniqueApplication.start():
    logging.info('Showing existing instance.')
    raise SystemExit(1)

# Delay loading resources until after single-instance check to ensure faster
# startup times of existing instance.
import subprocess
import os
import os.path
import re
import pickle
import math
import json

from PyQt4.QtCore import Qt, QObject, QEvent, pyqtSignal, QThread, QSize
from PyQt4.QtGui import (QApplication, QWidget, QVBoxLayout, QPalette,
                         QAbstractItemView, QListWidgetItem, QFont,
                         QBrush, QLineEdit, QListWidget)


DEFAULT_CONFIG = '''
{
    "monospace font": "monospace",
    "desktop paths": ["/usr/share/applications", "~/.local/share/applications"],
    "favorite apps": [],
    "icon size": 32,
    "translucent background": true
}
'''
CONFIG_PATH = '~/.spamalot_launcher.config.json'
CACHE_PATH = '~/.spamalot_launcher.cache'

ItemTypeRole = Qt.UserRole
ItemDataRole = Qt.UserRole + 1


def do_walk():
    NO_DISPLAY_PATTERN = re.compile(r'^\s*NoDisplay\s*=\s*true\s*$',
                                    flags=re.MULTILINE)
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

    with open(os.path.expanduser(CACHE_PATH), 'wb') as pickle_db:
        pickle.dump(database, pickle_db, protocol=2)
    return contents


class DictionaryProvider(object):

    def provide(self, search):
        if search.startswith('define ') and search != 'define ':
            item = QListWidgetItem(
                subprocess.check_output('dict {}; exit 0'.format(search[7:]),
                                        stderr=subprocess.STDOUT, shell=True))
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
                import sympy
                self.sympy = sympy
                # FIXME: needed?
                #sympy.init_printing()
            locals_ = {name: getattr(self.sympy, name) for name in
                (attribute for attribute in dir(self.sympy) if not attribute.startswith('_'))}
            for variable in ('x', 'y', 'z'):
                locals_[variable] = self.sympy.var(variable)
            prettify = self.sympy_prettify
        else:
            locals_ = {name: getattr(math, name) for name in
                (attribute for attribute in dir(math) if not attribute.startswith('_'))}
            for builtin in ('min', 'max', 'abs', 'hex', 'bin', 'int', 'oct', 'bool'):
                locals_[builtin] = getattr(__builtins__, builtin)
            prettify = str
        try:
            locals_['ans'] = self.ans
            self.ans = eval(search.lstrip('='), {'__builtins__': None}, locals_)
            item = QListWidgetItem(prettify(self.ans))
            item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
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
            subprocess.check_call(['which', search.split()[0]])
        except subprocess.CalledProcessError:
            pass
        else:
            item = QListWidgetItem(search)
            item.setForeground(Qt.red)
            item.setData(ItemTypeRole, 'executable')
            item.setData(ItemDataRole, search)
            yield item
        yield False


class ApplicationProvider(object):

    def __init__(self):
        if not os.path.isfile(os.path.expanduser(CACHE_PATH)):
            #print('Generating config file...')
            self.app_db = do_walk()
        #print('Loading config from file...')
        with open(os.path.expanduser(CACHE_PATH), 'rb') as pickle_db:
            self.app_db = pickle.load(pickle_db)

    def provide(self, search):
        for app in self.app_db:
            if ((search and (search.lower() in app['name'].lower() or search.lower() in app['exec'].lower())) or
                    (not search and app['name'] in config_options['favorite apps'])):
                item = (QListWidgetItem(KIcon(app['icon']), app['name'])
                    if app['icon'] else QListWidgetItem(app['name']))
                item.setData(ItemTypeRole, 'application')
                item.setData(ItemDataRole, app['path'])
                item.setSizeHint(QSize(1,36))
                yield item
        yield False


class DesktopSearchProvider(object):

    def provide(self, search):
        if not search:
            yield False
        baloo_dump = subprocess.check_output(['baloosearch', search]).decode('utf-8')
        paths = re.findall('\x1b\\[0;32m(.*)\x1b\\[0;0m', baloo_dump)
        for path in paths:
            item = QListWidgetItem(path)
            item.setForeground(Qt.blue)
            item.setData(ItemTypeRole, 'file')
            item.setData(ItemDataRole, path)
            yield item
        yield False


def do_search(search):
    items = []

    for provider in PROVIDERS:
        for result in provider.provide(search):
            if isinstance(result, QListWidgetItem):
                items.append(result)
            elif result:
                return items
            elif not result:
                break

    return items




class Worker(QObject):

    finished = pyqtSignal()
    new_items = pyqtSignal(list)

    def __init__(self, text, start_time):
        QObject.__init__(self)
        self.text = text
        self.time = start_time
        self.canceled = False

    def process(self):
        #print('Doing search...')
        if not self.canceled:
            self.new_items.emit(do_search(self.text))
        #print('searched for', self.text)
        self.finished.emit()


lastime = 0

def bla(items, worker):

    global lastime
    if worker.time < lastime:
        return
    lastime = worker.time

    ww = ws[:ws.index(worker)]
    for www in ww:
        www.canceled = True

    result_list_widget.clear()
    for item in items:
        result_list_widget.addItem(item)
    p = main_window.palette()
    search_bar.setPalette(p)
    lock = False



def repopulate(text):
    global th, ws
    #print('callback executed')
    tt = QThread()

    w = Worker(text, time.time())
    w.moveToThread(tt)

    tt.started.connect(w.process)
    w.finished.connect(tt.quit)
    w.finished.connect(w.deleteLater)
    w.new_items.connect(lambda x: bla(x, w))
    tt.finished.connect(tt.deleteLater)

    th.append(tt)
    ws.append(w)
    tt.start()

    p = main_window.palette()
    b = p.brush(QPalette.Highlight).color()
    p.setBrush(QPalette.Base, QBrush(b))
    search_bar.setPalette(p)

    th = [x for x in th if not sip.isdeleted(x)]
    ws = [x for x in ws if not sip.isdeleted(x)]


def cb_act(item):
    if item.data(ItemTypeRole) == 'application':
        #print('You opened the app:', item.data(ItemDataRole))
        subprocess.Popen(['exo-open', item.data(ItemDataRole)])
    elif item.data(ItemTypeRole) == 'file':
        #print('You opened the path:', item.data(ItemDataRole))
        subprocess.Popen(['dolphin', '--select', item.data(ItemDataRole)])
    elif item.data(ItemTypeRole) == 'executable':
        #print('You ran the application:', item.data(ItemDataRole))
        subprocess.Popen(item.data(ItemDataRole), shell=True)
    else:
        #print('This item cannot be opened.')
        return
    quit()

def cb_enter():
    result_list_widget.setFocus(True)
    result_list_widget.setCurrentRow(0)
    result_list_widget.itemActivated.emit(result_list_widget.item(0))

def quit():
    search_bar.clear()
    main_window.hide()

class Escaper(QObject):

    """Event filter to quit Qt application when escape is pressed."""

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress and event.key() == Qt.Key_Escape:
            quit()
            return True
        return False


class App(KUniqueApplication):

    _first_instance = True

    def newInstance(self):
        if App._first_instance:
            App._first_instance = False
            self.setQuitOnLastWindowClosed(False)
        else:
            if main_window.isVisible():
                quit()
            else:
                main_window.show()
                search_bar.setFocus(True)
        return 0

if not os.path.exists(os.path.expanduser(CONFIG_PATH)):
    with open(os.path.expanduser(CONFIG_PATH), 'w') as f:
        f.write(DEFAULT_CONFIG)
try:
    with open(os.path.expanduser(CONFIG_PATH)) as f:
        config_options = json.loads(f.read())
except Exception as err:
    logging.error(str(err))
    logging.warn('Using default configuration options.')
    config_options = json.loads(DEFAULT_CONFIG)


PROVIDERS = (DictionaryProvider(), CalculatorProvider(), CommandLineProvider(),
             ApplicationProvider(), DesktopSearchProvider())


app = App()

main_window = QWidget()
main_window.setWindowTitle('Spamalot Launcher')
if config_options['translucent background']:
    main_window.setAttribute(Qt.WA_TranslucentBackground)
main_window.setWindowFlags(Qt.FramelessWindowHint)
main_window.show()

layout = QVBoxLayout(main_window)

# FIXME: do_search should be part of a class that defines these instance
# variables instead of using global.
th = []
ws = []

search_bar = QLineEdit()
search_bar.textChanged.connect(repopulate)
search_bar.returnPressed.connect(cb_enter)

layout.addWidget(search_bar)

result_list_widget = QListWidget()
result_list_widget.setIconSize(QSize(*(config_options['icon size'],) * 2))
result_list_widget.setAlternatingRowColors(True)
result_list_widget.setTextElideMode(Qt.ElideMiddle)
result_list_widget.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
result_list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
result_list_widget.itemActivated.connect(cb_act)

p = result_list_widget.palette()
b = p.brush(QPalette.Base).color()
b.setAlphaF(0.9)
p.setBrush(QPalette.Base, QBrush(b))
b = p.brush(QPalette.AlternateBase).color()
b.setAlphaF(0.5)
p.setBrush(QPalette.AlternateBase, QBrush(b))
main_window.setPalette(p)

layout.addWidget(result_list_widget)

main_window.installEventFilter(Escaper(main_window))

repopulate('')  # Populate with favorite applications.

app.exec_()
