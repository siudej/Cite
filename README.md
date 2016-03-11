# Citation fetcher with customizable LaTeX/BibTeX output

PyQt GUI and a separate fetching engine for finding mathematics related citations on 
[arXiv](http://front.math.ucdavis.edu), [MathSciNet](http://www.ams.org/mathscinet/) and [zbMATH](https://zbmath.org).

Assuming required packages are present:
* Application can be started with `cite.py`.
* On OS X with Anaconda: run `installMac.sh` to install Services (user confirmation needed) and add `cite` to PATH.
* On OS X with Cite.app: Double click on Services to install, then put Cite.app in /Applications folder.

### General requirements
* LaTeX/BibTeX
* `PyQt` (4 or 5)
* `bibtexparser` Python package

On OS X I would recommend installing Anaconda Python, then `bibtexparser` via `pip`. Another option is to use a standalone App (see the end of this document for more about OS X).

### Search format
Search supports many field specifiers (author, title, journal, year, ...) as well as logical connectors (and/or/not). The search format is uniform for all databases, with all differences handled behind the scene.

Example search:
```
au:siudeja laugesen
2011
```
will find my papers written with my best collaborator, published in 2011.

It is also possible to feed a fully formatted bibitem or BibTeX entry as a search query, even including all the LaTeX formatting commands.

### Output
Application supports raw BibTeX output, and custom LaTeX outputs: 
* font style can be chosen for authors, title, journal, ...
* bibitem labels can be automatically generated, or preserved if given in the search query
* links to databases can be automatically added

Batch processing is also possible. A list of citations can be processed to find links to databases, create BibTeX file, or to reformat/uniformize the LaTeX output.

### System integration
The main script `cite.py` also accepts querries as parameters, or through stdin. In this case no GUI is created (PyQt is not needed) and the output is sent to stdout. This allows integration with text editors. One could use the following in Vim:
```
nmap ,bb !!cite.py<CR>
vmap ,bb !cite.py<CR>
nmap ,ba !!cite.py -a<CR>
vmap ,ba !cite.py -a<CR>
```
to feed a line, or a selection to the script.

The `,ba` command can be used to force arXiv search. Other options are also available.

### Application settings 
Settings are saved in settings.xml file in the script's folder. This file is processed by both terminal and GUI versions. Hence it is convenient to set the settings in GUI, although the XML file can also be modified.

In PyQt, the settings are handled by a slightly modified [pyqtconfig](https://github.com/mfitzp/pyqtconfig) scipt (supplied).

### OS X
A standalone OS X app should work on OS X 10.10 and 10.11, although constantly changing system environment makes it hard to maintain a working package. The App is in `osx/` subfolder, together with two Automator scripts. The only requirement to run the App is a working LaTaX installation. And it needs to be placed in `/Applications`.

The supplied Automator scripts allow filtering of any selected text through the application.
The output can either replace the selection, or appear in a new TextEdit window. Then right click on a selected text and look for Cite in Services.

## Warning
This is an alpha version.

Some features are not yet fully implemented, and the documentation is lacking.
