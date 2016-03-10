r"""
Main script for terminal interface.

Does not need PyQt.

Accepts:
    query as first script parameter
    list of options in the form -\w+ then second parameter becomes query
    query from stdin
    query from raw_input

Default behavior:
    Uses 'batch' MR/Zbl/... numbers options.
    Uses Batch fetcher unless a specific fetcher is in parameters.
    Hence it checks all sources looking for a unique match.

See optionsFromQuery for available options.
"""

import re
import os

# fetchers
from arxiv import ArXiv
from msn import MathSciNet
from zbl import Zbl
from batch import Batch
from fetch import fixQuery


settings = None
convert = {'int': lambda x: int(x),
           'float': lambda x: float(x),
           'str': lambda x: str(x),
           'unicode': lambda x: str(x),
           'bool': lambda x: x.lower() == 'true'}


def getSettings():
    """ Read settings from xml file. """
    global settings
    from collections import defaultdict
    settings = defaultdict(str)
    try:
        path = os.path.dirname(os.path.realpath(__file__))
        with open(path + '/settings.xml') as f:
            xml = f.read()
        import xml.etree.cElementTree as et
        et = et.fromstring(xml)[0]
        for e in et:
            # change builtin type name to the named type
            try:
                conv = convert[e.attrib['type']]
                settings[e.attrib['id']] = conv(e.text)
            except:
                pass
    except:
        print "No settings file. Continuing with a minimal configuration. "
    settings['fetcher'] = Batch
    # use batch formatting
    settings["type"] = 'batch'
    settings["html"] = False
    settings["count"] = 0


def getQuery():
    """ Read user's query string from wherever you can. """
    import sys
    options = ""
    args = sys.argv[1:]
    if args and args[0][0] == '-':
        options = re.sub(r'\W', '', args[0])
        args = args[1:]
        if options:
            options = '(?' + options + ') '
    query = ' '.join(args)
    if args and re.sub(r"\W", "", query):
        return options + query
    if not sys.stdin.isatty():
        # query from stdin
        query = options + sys.stdin.read()
        query = fixQuery(query)
        return query
    else:
        # ask for it
        return options + raw_input("Search query: ")


def optionsFromQuery(query):
    """ Extract (?...) options from query. """
    m = re.match("(?si)((?:\(\?[^)]*\)|\s)+)?(.*)", query)
    query = m.group(2)
    try:
        options = re.sub(r"\W", "", m.group(1))
        # last fetcher wins
        options = re.sub(r"[mza](?=.*[mza])", "", options)
    except:
        return query
    if 'b' in options:
        # force bibtex output
        settings["bibtexOut"] = True
    elif 'f' in options or 'l' in options:
        # force formatted output
        settings["bibtexOut"] = False
    if 's' in options:
        # use search mode formatting
        settings["type"] = 'search'
    elif 'B' in options:
        # use batch mode formatting
        settings["type"] = 'batch'
    if 'm' in options:
        # force MSN
        settings["fetcher"] = MathSciNet
    elif 'z' in options:
        # force zbMATH
        settings["fetcher"] = Zbl
    elif 'a' in options:
        # force arXiv
        settings["fetcher"] = ArXiv
    m = re.search(r'(\d+)', options)
    if m and m.group(1):
        # find this many references
        settings["count"] = int(m.group(1))
    return query


def startTerminal():
    """ Start searching. """
    # get settings
    getSettings()
    query = getQuery()
    query = optionsFromQuery(query)
    if not re.sub(r"\W", "", query):
        return 0

    # extract separate queries
    count = settings["count"]  # count from options
    if count <= 0:
        # count from settings file
        count = settings[settings["type"] + "Count"]
    # make sure count makes sense
    try:
        count = int(count)
        assert count > 0
    except:
        count = 3
    # run the chosen fetcher
    fetcher = settings['fetcher']()
    results = fetcher(query, count, settings)[1]
    if fetcher.number > 0:
        print results
    else:
        print query
    return 0


if __name__ == "__main__":
    startTerminal()
