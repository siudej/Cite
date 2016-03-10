"""
Main application window.

Should work with PyQt4 and PyQt5.
"""

# TODO morph batch text into browser with links
#   finish remove ...
#   add remove/open options to settings
#   show bibtex changing to hide bibtex to keep current format

import re
import os
import xml.dom.minidom as dm
try:
    import xml.etree.cElementTree as et
except:
    import xml.etree.ElementTree as et

import sip
sip.setapi("QString", 2)
sip.setapi("QVariant", 2)
try:
    from PyQt5.QtWidgets import QMainWindow, QApplication, QTextBrowser
    from PyQt5.QtCore import QSize, QPoint, pyqtSlot, QEvent, Qt
    from citeGUI5 import Ui_Cite
except:
    from PyQt4.QtGui import QMainWindow, QApplication, QTextBrowser
    from PyQt4.QtCore import QSize, QPoint, pyqtSlot, QEvent, Qt
    from citeGUI4 import Ui_Cite

# fix for missing qt_plugin in OS X App
try:
    if not QApplication.libraryPaths():
        QApplication.addLibraryPath(str(os.environ['RESOURCEPATH'] + '/qt_plugins'))
except:
    pass

# fetchers
from arxiv import ArXiv
from fetch import Fetch, fixQuery
from batch import batchSplit, Batch
from msn import MathSciNet, MRef
from zbl import Zbl
from progress2 import Progress


class Cite(Ui_Cite, QMainWindow):

    """ Main application window. """

    def __init__(self):
        """ Initialize main window. """
        QMainWindow.__init__(self)
        self.setupUi(self)
        self.resize(QSize(settings.get('citewidth'),
                          settings.get('citeheight')))
        self.move(QPoint(settings.get('citex'),
                         settings.get('citey')))
        self.tabWidget.tabBar().setCurrentIndex(0)
        self.searchTab.setFocus()
        self.setWindowTitle('Cite')
        self.show()
        self.raise_()

        self.linkSettings()

        self.searchQuery.installEventFilter(self)
        self.text = self.bibtext = self.lastquery = ""
        self.batchBibtext = self.batchText = ""
        self.neverOpened = True

    def linkSettings(self):
        """ Link widgets to settings to enable automatic saving. """
        # find all batch/search pairs and copy the options
        for name in {'MRZbl', 'IncludeDOIURL', 'DOIURL', 'Arxiv'}:
            search = self.__dict__['search' + name]
            batch = self.__dict__['batch' + name]
            batch.addItems([search.itemText(i) for i in range(search.count())])
            batch.setCurrentIndex(search.currentIndex())

        # find all widgets with data in options tab
        for name, widget in self.__dict__.items():
            try:
                if self.optionsTab.isAncestorOf(widget) and \
                        not re.match(r'line|group|label|\w+Tab', name):
                    settings.add_handler(name, widget)
            except:
                pass
        # batch separator
        settings.add_handler('separator', self.separator)
        try:
            path = os.path.dirname(os.path.realpath(__file__))
            open(path + '/settings.xml', 'r')
        except:
            # save settings file if it does not exist
            # defualts are not saved so move them to the values
            settings.set_many(settings.defaults)
            self.save_settings()

    def save_settings(self):
        """ Update settings file. """
        root = et.Element("CiteXML")
        root = settings.getXMLConfig(root)
        s = dm.parseString(et.tostring(root)).toprettyxml(indent="    ")
        path = os.path.dirname(os.path.realpath(__file__))
        with open(path + '/settings.xml', 'wb') as f:
            print >>f, s

    def closeEvent(self, event):
        """ Make sure settings are saved. """
        settings.set('citex', self.pos().x())
        settings.set('citey', self.pos().y())
        settings.set('citeheight', self.size().height())
        settings.set('citewidth', self.size().width())
        self.save_settings()
        event.accept()

    def HTMLsafe(self, text, bibtex):
        """ Add links and deal with <& characters. """
        text = re.sub(r'&', r'&amp;', text)
        text = "<p>" + re.sub(r'<(?!/?(font|h2>))', r'&lt;', text) \
            .replace('\n\n', '</p><p>')
        if bibtex:
            text = text.replace('\n', '<br>')
            text = re.sub(
                r"arxiv\s*=\s*\{(.*?)\}",
                r'arxiv = {<a href="http://front.math.ucdavis.edu/\1">\1</a>}',
                text)
            text = re.sub(
                r"mrnumber\s*=\s*\{(.*?)\}", r'mrnumber = {<a href="http://' +
                r'www.ams.org/mathscinet-getitem?mr=\1">\1</a>}', text)
            text = re.sub(
                r"link\s*=\s*\{(.*?)\}", r'link = {<a href="\1">\1</a>}', text)
            text = re.sub(
                r"url\s*=\s*\{(.*?)\}", r'url = {<a href="\1">\1</a>}', text)
            text = re.sub(
                r"doi\s*=\s*\{(.*?)\}",
                r'doi = {<a href="http://dx.doi.org/\1">\1</a>}', text)
            text = re.sub(
                r"zbl\s*=\s*\{(.*?)\}",
                r'zbl = {<a href="http://zbMATH.org/?q=an:\1">\1</a>}', text)
        else:
            text = re.sub(
                r"\\arxiv\{(.*?)\}",
                r'\\arxiv{<a href="http://front.math.ucdavis.edu/\1">\1</a>}',
                text)
            text = re.sub(
                r'\\mref\{(.*?)\}', r'\\mref{<a href="http://www.' +
                r'ams.org/mathscinet-getitem?mr=\1">\1</a>}', text)
            text = re.sub(
                r'\\url\{(.*?)\}', r'\\url{<a href="\1">\1</a>}', text)
            text = re.sub(r"\\doi\{(.*?)\}",
                          r'\\doi{<a href="http://dx.doi.org/\1">\1</a>}', text)
            text = re.sub(r"\\zbl\{(.*?)\}",
                          r'\\zbl{<a href="http://zbMATH.org/?q=an:\1">\1</a>}',
                          text)
        return text

    @pyqtSlot()
    def on_formatBibtex_clicked(self):
        """ Run Bibtex to get formatted tex string. """
        query = self.searchQuery.toPlainText()
        if re.match(r'(\n|\s|\r)*$', query):
            return
        fetch = Fetch()
        fetch.setBibtex(query)
        if fetch.refs == "":
            return
        dct = settings.as_dict()
        dct['html'] = True
        dct['type'] = 'search'
        dct['bibtexOut'] = False
        self.text = self.HTMLsafe(fetch.getRefs(**dct), False)
        self.lastBibtex = False
        self.quickResults.setText(self.text)

    @pyqtSlot()
    def on_showBibtex_clicked(self):
        """ Show unformatted bibtex string. """
        if self.bibtext:
            self.quickResults.setText(self.HTMLsafe(self.bibtext, True))
            self.lastBibtex = True

    @pyqtSlot()
    def on_reformat_clicked(self):
        """ Run Fetcher to get new formatted string. """
        if not self.bibtext:
            return
        fetch = Fetch()
        fetch.setBibtex(self.bibtext)
        dct = settings.as_dict()
        dct['html'] = True
        dct['type'] = 'search'
        dct['bibtexOut'] = False
        self.text = self.HTMLsafe(fetch.getRefs(**dct), False)
        self.lastBibtex = False
        self.quickResults.setText(self.text)

    @pyqtSlot()
    def on_savedShowBibtex_clicked(self):
        """ Show BibTex in results tab. """
        currtab = self.resultsTabs.currentWidget()
        # remember what is shown in the tab
        currtab.formattedtext = self.HTMLsafe(currtab.bibtext, True)
        currtab.lastBibtex = True
        self.resultsTabs.currentWidget().setText(currtab.formattedtext)

    @pyqtSlot()
    def on_savedReformat_clicked(self):
        """ Run Fetcher to get new formatted string in a results tab. """
        currtab = self.resultsTabs.currentWidget()
        fetch = Fetch()
        fetch.setBibtex(currtab.bibtext)
        dct = settings.as_dict()
        dct['html'] = True
        dct['type'] = 'search'
        dct['bibtexOut'] = False
        text = fetch.getRefs(**dct)
        currtab.formattedtext = self.HTMLsafe(text, False)
        currtab.lastBibtex = False
        self.resultsTabs.currentWidget().setText(currtab.formattedtext)

    @pyqtSlot()
    def on_arxiv_clicked(self):
        """ Execute arxiv search. """
        if QApplication.keyboardModifiers() == Qt.ControlModifier:
            self.startWorker(ArXiv(), "Searching arXiv ...", website=True)
        else:
            self.startWorker(ArXiv(), "Searching arXiv ...")

    @pyqtSlot()
    def on_msn_clicked(self):
        """ Execute MathSciNet search. """
        if QApplication.keyboardModifiers() == Qt.ControlModifier:
            self.startWorker(MathSciNet(), "Searching MathSciNet ...",
                             website=True)
        else:
            self.startWorker(MathSciNet(), "Searching MathSciNet ...")

    @pyqtSlot()
    def on_mref_clicked(self):
        """ Execute MRef search. """
        self.startWorker(MRef(), "Searching MRef ...")

    @pyqtSlot()
    def on_zbl_clicked(self):
        """ Execute MathSciNet search. """
        self.startWorker(Zbl(settings.get("searchMrefWithZbl")),
                         "Searching zbMATH ...")

    @pyqtSlot()
    def on_allThree_clicked(self):
        """ Run all fetchers at the same time. """
        self.startWorker([Zbl(), MathSciNet(), ArXiv()],
                         "Searching everywhere ...")

    def startWorker(self, fetcher, job, website=False):
        """ Generic execution of a fetcher. """
        query = self.searchQuery.toPlainText()
        query = fixQuery(query)
        if re.match(r'(\n|\s|\r)*$', query):
            return
        self.quickResults.setText(job)
        dct = settings.as_dict()
        dct['html'] = True
        dct['type'] = 'search'
        if website:
            dct["website"] = True
        count = settings.get('searchCount')
        try:
            l = len(fetcher)
            # make a copy of dct for threading safety
            args = [(query, count, dict(dct)) for _ in range(l)]
            progress = Progress(fetcher, args, job=job)
        except:
            progress = Progress(fetcher, [query, count, dct], job=job)
        progress.exec_()
        if progress.res and not website:
            for record in progress.res:
                self.bibtext = self.text = ''
                bib, txt = record['result']
                self.bibtext += '\n\n' + bib
                if record['number']:
                    self.text += '\n<h2>{}: {} result{}.</h2>\n' \
                        .format(record['name'], record['number'],
                                's' if record['number'] > 1 else '') + txt
                else:
                    self.text += '\n<h2>{} failed!</h2>' \
                        .format(record['name'])
            self.lastquery = query
        elif website:
            # print progress.res[0]['result'][1]
            self.quickResults.setHtml(progress.res[0]['result'][1])
            self.text = progress.res[0]['result'][1]
            self.bibtext = ""
            # FIXME allow open in saved
            return 0
        else:
            # worker failed
            self.quickResults.append(
                "<br><strong>Failed to generate results ...</strong>")
            return 0
        self.text = self.HTMLsafe(self.text, False)
        if settings.get("bibtexOut"):
            self.quickResults.setText(self.HTMLsafe(self.bibtext, True))
            self.lastBibtex = True
        else:
            self.quickResults.setText(self.text)
            self.lastBibtex = False

    @pyqtSlot()
    def on_openInResults_clicked(self):
        """ Open fetched results in new tab. """
        if self.bibtext == "" or self.lastquery == "":
            return
        self.newTab(self.text, self.bibtext, self.lastBibtex,
                    self.lastquery.replace('\n', ';'))

    def newTab(self, text, bibtext, showBibtex, query):
        """ Create new Tab with results. """
        if self.neverOpened:
            self.resultsTabs.removeTab(0)
            self.neverOpened = False
            self.savedReformat.setEnabled(True)
            self.savedShowBibtex.setEnabled(True)
            self.openInBatch.setEnabled(True)
        tab = QTextBrowser()
        # enable editing
        # TODO save bibtex before reformat
        tab.setTextInteractionFlags(tab.textInteractionFlags() |
                                    Qt.TextEditable | Qt.TextEditorInteraction)
        tab.setOpenExternalLinks(True)
        tab.formattedtext = text
        tab.bibtext = bibtext
        tab.lastBibtex = showBibtex

        if showBibtex:
            tab.setText(self.HTMLsafe(bibtext, True))
        else:
            tab.setText(text)

        self.tabWidget.tabBar().setCurrentIndex(1)
        self.resultsTabs.addTab(tab, query)
        self.resultsTabs.tabBar().setCurrentIndex(self.resultsTabs.count()-1)
        tab.setFocus(True)

    def on_resultsTabs_tabCloseRequested(self, index):
        """ Remove a tab with saved data. """
        widget = self.resultsTabs.widget(index)
        self.resultsTabs.removeTab(index)
        widget.setParent(None)
        widget.deleteLater()
        if self.resultsTabs.count() == 0:
            self.savedReformat.setEnabled(False)
            self.savedShowBibtex.setEnabled(False)
            self.openInBatch.setEnabled(False)
            self.resultsTabs.addTab(self.emptyResults, 'No results')
            self.neverOpened = True

    def eventFilter(self, source, event):
        """ Add/remove a few keyboard and mouse events. """
        if source is self.searchQuery:
            if event.type() == QEvent.KeyPress:
                if event.key() == Qt.Key_Return:
                    if event.modifiers() == Qt.ShiftModifier:
                        self.on_arxiv_clicked()
                        return True
                    elif event.modifiers() == Qt.ControlModifier:
                        self.on_msn_clicked()
                        return True
                    elif event.modifiers() == Qt.AltModifier:
                        self.on_zbl_clicked()
                        return True
        return QMainWindow.eventFilter(self, source, event)

    @pyqtSlot()
    def on_batchRun_clicked(self):
        """ Run sequence of fetchers on a list of queries from Batch Tab. """
        query = self.batchEdit.toPlainText()
        query = fixQuery(query)
        if re.match(r'\W+$', query):
            return
        self.batchBibtext = self.batchText = ""
        dct = settings.as_dict()
        dct['html'] = True
        dct['type'] = 'batch'
        count = settings.get('batchCount')
        queries, dct = batchSplit(query, dct)
        fetcherdict = {'arXiv': ArXiv, 'MathSciNet': MathSciNet,
                       'zbMATH': Zbl, 'Batch': Batch}

        fetcher = fetcherdict[self.batchFetcher.currentText()]
        args = []
        fetchers = []
        for query in queries:
            # FIXME put otherID in the constructor below based on settings
            fetchers.append(fetcher())
            # make a copy of dct for threading safety
            args.append((query, count, dict(dct)))
        progress = Progress(fetchers, args, job="Searching ...")
        progress.exec_()
        result = ""
        self.batchLastBibtex = settings.get('bibtexOut')
        for record in progress.res:
            if record['number'] == 0:
                color = 'red'
                s = '% No match found for\n\n{}' \
                    .format(record['query'])
            elif record['nonunique']:
                color = 'darkmagenta'
                s = '% {} matches found for\n\n{}\n\n% results:\n\n{}\n\n% end' \
                    .format(record['number'], record['query'],
                            record['result'][1])
                self.batchBibtext += '% start nonunique\n\n{}% end nonunique\n\n' \
                    .format(record['result'][0])
            else:
                color = 'black'
                s = record['result'][1]
                self.batchBibtext += record['result'][0]
            result += '<font color="{}"><p>{}</p></font>' \
                .format(color, self.HTMLsafe(s, settings.get('bibtexOut')))
        self.batchEdit.setText(result)
        self.batchText = result

    @pyqtSlot()
    def on_batchOpenInResults_clicked(self):
        """ Open batch results in a new Saved Tab. """
        if not self.batchText:
            return
        option = self.batchOpenOptions.currentText()
        text = self.batchText
        bib = self.batchBibtext
        if 'unique' in option:
            text = re.sub(r'(?si)<font color="(red|darkm).*?(?=<font color=|$)',
                          '', text)
            bib = re.sub(r'(?si)% start nonunique.*?% end nonunique\n?',
                         '', bib)
        elif 'results' in option:
            text = re.sub(r'(?si)<font color="red.*?(?=<font color=|$)',
                          '', text)
            text = re.sub(r'(?si)<p>% \d+ match.*?% results:</p>', '', text)
            text = re.sub(r'(?si)<p>% end</p>', '', text)
            bib = re.sub(r'(?si)% (start|end) nonunique', '', bib)
        self.newTab(text, bib, self.batchLastBibtex,
                    "Batch results")

    @pyqtSlot()
    def on_batchRemove_clicked(self):
        """ Remove parts of the fetched text. """
        option = self.batchRemoveOptions.currentText()
        text = self.batchText
        bib = self.batchBibtext
        if option == 'unique':
            text = re.sub(r'(?si)<font color="black.*?(?=<font color=|$)',
                          '', text)
            bib = ''.join(re.findall(
                r'(?si)(?<=start nonunique).+?(?=% end nonunique)', bib))
        # FIXME finish other options
        self.batchText = text
        self.batchBibtext = bib
        self.batchEdit.setText(self.batchText)

    @pyqtSlot()
    def on_openInBatch_clicked(self):
        """ Move the content to batch tab. """
        currtab = self.resultsTabs.currentWidget()
        self.batchEdit.setText(currtab.formattedtext)
        self.batchText = currtab.formattedtext
        self.batchBibtext = currtab.bibtext
        self.batchLastBibtex = currtab.lastBibtex
        self.tabWidget.tabBar().setCurrentIndex(3)
        self.batchEdit.setFocus(True)


settings = None
window = None

def startApp():
    """ Initialize the application. """
    global settings, window
    from config import ConfigManager
    settings = ConfigManager()
    settings.set_default('citeheight', 500)
    settings.set_default('citewidth', 700)
    settings.set_default('citex', 0)
    settings.set_default('citey', 0)
    try:
        path = os.path.dirname(os.path.realpath(__file__))
        with open(path + '/settings.xml', 'rb') as f:
            root = et.fromstring(f.read())
            settings.setXMLConfig(root)
            settings.set_defaults(settings.config)
    except:
        pass
    import sys
    app = QApplication(sys.argv)
    window = Cite()
    sys.exit(app.exec_())


if __name__ == "__main__":
    startApp()
