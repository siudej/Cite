""" setuptools file for py2app. """
from setuptools import setup
import sys
sys.setrecursionlimit(1500)

# necessary modules
include = ['sip', 'PyQt5', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets',
           'bibtexparser']
# list of all modules to exclude
import pkgutil
exclude = set(tup[1] for tup in pkgutil.iter_modules())
exclude.difference_update(include)
# unnecessary PyQt5 pieces
exclude.update(['PyQt5.Enginio', 'PyQt5.Qt', 'PyQt5.QtBluetooth',
                'PyQt5.QtDesigner', 'PyQt5.QtHelp', 'PyQt5.QtMacExtras',
                'PyQt5.QtMultimedia', 'PyQt5.QtMultimediaWidgets',
                'PyQt5.QtNetwork', 'PyQt5.QtOpenGL', 'PyQt5.QtPositioning',
                'PyQt5.QtPrintSupport', 'PyQt5.QtQml', 'PyQt5.QtQuick',
                'PyQt5.QtQuickWidgets', 'PyQt5.QtSensors',
                'PyQt5.QtSerialPort', 'PyQt5.QtSql', 'PyQt5.QtSvg',
                'PyQt5.QtTest', 'PyQt5.QtWebChannel', 'PyQt5.QtDBus',
                'PyQt5.QtWebEngineWidgets', 'PyQt5.QtWebKit',
                'PyQt5.QtWebKitWidgets', 'PyQt5.QtWebSockets',
                'PyQt5.QtXml', 'PyQt5.QtXmlPatterns',
                'PyQt5._QOpenGLFunctions_2_0', 'PyQt5.uic'])


APP = ['py2app/start.py']
OPTIONS = {'argv_emulation': False,
           'includes': include,
           'excludes': list(exclude),
           'dylib_excludes': ['QtCLucene.framework', 'QtDBus.framework',
                              'QtNetwork.framework', 'QtQml.framework',
                              'QtQuick.framework', 'QtPrintSupport.framework'],
           'semi_standalone': True,
           'site_packages': False,
           'qt_plugins': ['platforms/libqcocoa.dylib',
                          # 'accessible/libqtaccessiblewidgets.dylib'
                          ],
           'resources': ['citeGUI5.py', 'arxiv.py', 'msn.py', 'zbl.py',
                         'cite.py', 'citeWindow.py', 'citeTerminal.py',
                         'batch.py', 'progress2.py', 'bibtex.py', 'config.py',
                         'default.bst', 'fetch.py', 'settings.xml',
                         'py2app/cite', 'doc'],
           }

setup(
    app=APP,
    name="Cite",
    version="0.1",
    author="Bartek Siudeja",
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
