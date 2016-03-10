""" Abstract class for fetching the results from web engines. """

import urllib
import urllib2
import re
import unicodedata
from bibtex import BibTex
from collections import defaultdict


class Fetch(object):

    """
    Abstract class handling GET/POST requests.

    class variable url: holds main part of the link to web engine
    self.refs: holds bibtex string
    self.nonunique: true if exactly one result found
    self.number: number of results
    """

    url = ""
    correction = 0
    onceMax = 100
    more = ""

    def __init__(self, otherID=False):
        """
        Set main search engine url in subclass.

        otherID can be used to instruct fetcher to run other fetchers.

        Even if user requests 1 record, it may still be nonunique, since
        fetcher might find more than 1 and return just 1.
        """
        self.refs = []
        self.nonunique = True
        self.bibitem = ""
        self.number = 0
        self.otherID = otherID

    def __call__(self, query, count, dct):
        """
        Make object act like a function.

        Allows for easy pickling and calling the object in multiprocessing.

        Returns BibTex and LaTex outputs.
        """
        if "website" in dct and dct["website"]:
            return '', self.getWebsite(query, count)
        else:
            self.fetch(query, count)
            return self.refs, self.getRefs(**dct)

    def fetch(self, query, count=100):
        """ Process the query and execute search. """
        self.count = count
        query = fixQuery(query)
        query_dict = self._preprocessQuery(query)
        if not query_dict:
            self.number = 0
            self.refs = ""
            self.nonunique = True
            return False
        query = self._formatQuery(query_dict)
        query = urllib.urlencode(query) + "&"
        self.query = query
        found = 0
        allrefs = []
        while found < count:
            full_url = self.url + query
            if self.more:
                full_url += self.more + str(found+self.correction)
            try:
                data = urllib2.urlopen(full_url).read()
                self._processResults(data)
                self._cleanupBibTex(count)
            except:
                self.number = 0
            if self.number == 0:
                break
            allrefs.append(self.refs)
            found += self.number
            if not self.more or found < self.onceMax:
                break
        self.refs = '\n\n'.join(allrefs)
        # result can be nonunique even if user wants to see 1 record
        self.nonunique = found > 1
        if found > count:
            # too many results, truncate
            self.refs = '\n\n'.join(self.refs.split('\n\n')[:count])
            found = count
        self.number = found
        if self.number == 0:
            self.refs = ""
            self.nonunique = True
            return False
        return True

    def getWebsite(self, query, count=100):
        """ Execute search but do not postprocess the results. """
        query = fixQuery(query)
        query_dict = self._preprocessQuery(query)
        query = self._formatQuery(query_dict)
        query = urllib.urlencode(query) + "&"
        full_url = self.website + query
        data = urllib2.urlopen(full_url).read()
        data = self._cleanWebsite(data)
        self.number = 1
        self.refs = ""
        return data

    def _preprocessQuery(self, query):
        """
        Turn query into a dict with bibtex style fields.

        Handles bibtex, separate fields, and full citation forms of querries.

        Each parser can later format it.
        """
        if re.match(r"(?si)(\n|\s|\r)*@\w+\{", query):
            return self._bibtexQuery(query)
        elif re.match(r"(?si)\\(bibitem|text|emph|newblock|bf\s|it\s)", query):
            # seems like LaTeX formatted full citation
            return self._citationQuery(query)
        elif re.match(r"(?si).*\b(\w{2,3}|date|year):", query):
            # found a field specifier
            return self._fieldsQuery(query)
        elif re.match(r"(?si)(.*\n)?\s*(\w:|\d{4,})", query):
            # line starts with short query field or date?
            return self._fieldsQuery(query)
        elif len(query) > 40 and len(query.split("\n")) < 3:
            # long query with few lines
            return self._citationQuery(query)
        else:
            # try guessing fields
            # if the query is a full citation there should be enough to get it
            # as a genral field
            return self._fieldsQuery(query)

    def _bibtexQuery(self, query):
        """ Turn query into bibtex dictionary. """
        import bibtexparser
        from bibtexparser.bparser import BibTexParser
        parser = BibTexParser()
        parser.customization = homogeneize_latex_encoding
        bib = bibtexparser.loads(query, parser=parser)
        if bib.entries:
            # only the first record
            record = bib.entries[0]
            # clean up entries
            if "author" in record:
                # just last name
                record["author"] = re.sub(r',.*?(and\s*|$)', ' ',
                                          record['author'])
            if "title" in record:
                record["title"] = self._citationQuery(record["title"])[0][1]
            if "journal" in record:
                record["journal"] = self._citationQuery(record["journal"])[0][1]
            if "year" in record:
                record["date"] = record["year"]
            # only use a few fields
            # TODO add numbers
            return [(k, v) for k, v in record.items() if k in
                    {"author", "title", "journal", "mrnumber", "date",
                     "arxiv", "zbl"}]
        else:
            return []

    def _citationQuery(self, query):
        """ Save bibitem and strip formatting from query. """
        # get rid of bibitem and save it
        match = re.match(
            r"\s*(\\bibitem\s*(\[.*?\])?\s*\{(\w|\{(\{.*?\}|[^{}])*?\}|\+)*\})",
            query)
        if match:
            self.bibitem = match.group(1)
        query = re.sub(
            r"\s*(\\bibitem\s*(\[.*?\])?\s*\{(\w|\{(\{.*?\}|[^{}])*?\}|\+)*\})",
            "", query)

        # cleanup
        # remove links and numbers from the end
        query = re.sub(r"(?si)mr\d{6,}", "", query)
        query = re.sub(r"(?si)(https?:|\\doi|\\mref|\\arxiv|MR\s*:?\s*\d{4,}|" +
                       r"zbl\s*\d+|arxiv:?\s*\d+|\\url|\\href).*", "", query)
        # remove tex commands
        query = re.sub(r"(?si)\\[A-Za-z]{2,}", "", query)
        # remove accents, but not {letter}
        query = re.sub(r"(?si)\{\\'\{\\i\}\}|\\'\\i\s", "i", query)
        query = re.sub(r"(?si)\\c s", "s", query)
        query = re.sub(r"(?si)\{\\l\}", "l", query)
        query = re.sub(r"(?si)\\\W\s?|\\\w(?=\\|\{)", "",
                       query).replace('~', ' ')
        # remove formulas
        query = re.sub(r"(?si)\$.*?\$", "", query)
        # remove a few words
        query = re.sub(r"(?si)\(electronic\)", " ", query)
        query = re.sub(r"(?si)(dedicated\s+to).*", " ", query)
        # remove certain characters
        query = re.sub(r"[][{}?%#():`]", "", query)
        query = re.sub(r"[&=/,']", " ", query)
        # remove short words
        query = re.sub(r"(?si)\b(and|not|und|art|vol|eds|isbn|inc|the|with)\b",
                       " ", query)
        query = re.sub(r"(?si)\b[A-Za-z]{1,2}\b", " ", query)
        # remove all numbers except for years (4 digits)
        query = re.sub(r"(?si)\b\d+\s*-+\s*\d+\b", " ", query)
        query = re.sub(r"(?si)\b(\d{1,3}|\d{5,})\b", " ", query)
        # remove preprint and other endings
        query = re.sub(r"(?si)\b(preparation|arxiv|preprint|to\s+appear|" +
                       r"submitted|translated\s+from).*",
                       " ", query)
        # remove publisher names, places and some other words
        query = re.sub(r"Birkhauser|Springer|New York|Paris|Heidelberg|" +
                       r"Boston|Basel|Grenoble|Verlag",
                       "", query)
        # short word with . is most likely an abbreviation
        query = re.sub(r"(\b[a-zA-Z]{,4})\.", r"\1*", query)
        # remove a few more characters
        query = re.sub(r"[-.]", " ", query)
        query = re.sub(r"\\", "", query)
        query = re.sub(r"\s+\*+(\s+|$)", " ", query)
        # remove extra white characters
        query = re.sub(r"(?si)([\s\n\r]+)", " ", query).strip()
        year = re.findall(r'\d{4}', query)
        if year and len(year) == 1:
            # extract year as separate field
            query = re.sub(r'\d{4}', ' ', query)
            return [('none', query), ('date', year[0])]
        else:
            return [('none', query)]

    def _fieldsQuery(self, query):
        r"""
        Detect fields and form a list.

        List format:
        ['',                # empty
        then repeated
            ') and \n not (',    # parentheses and logic with new line
            ('field', 'value'),

        The same query can contain many values for the same field.

        """
        # cleanup
        # remove tex commands
        query = re.sub(r"(?si)\\[A-Za-z]{2,}", "", query)
        # remove accents, but not {?}
        query = re.sub(r"(?si)\\\W|\\\w(?=\\|\{)", "", query).replace('~', ' ')
        # remove formulas
        query = re.sub(r"(?si)\$.*?\$", "", query)
        # remove {}&?%=/#.
        query = re.sub(r"[{}&?%=/#.]", "", query)

        # TODO pyparse could make this easier
        # try to find the fields by adding \n before each field indicator
        query = re.sub(r"(?<=[\s()])([a-zA-Z]{2,3}|date|year|type):",
                       r"\n\1:", query)
        # start with new line to ensure parentheses/logic before the first query
        query = '\n' + query
        # split preserving and/or/not/(/) at the boundaries of the fields/lines
        # this allows for rebuilding of a complex query with parentheses
        lines = re.split(
            r"(?si)((?:[\s()]|and|not|or)*" +  # before new line
            r"(?:\n+|$)" +                     # new line or end
            r"(?:[\s()]|and|not|or)*)",        # after new line
            query)
        lst = []
        for line in lines:
            if re.match(r"(?si)([\s()\n]|and|or|not)*$", line):
                # parentheses and/or logic
                lst.append(line)
                continue
            # detect date (range) with or without field
            date = re.match(
                r"(?si)((?:py|yr|dt|date|year):[\D]*?)?" +     # field or not
                r"([<=>]?\s*\d{4}(\s*-+\s*\d{4}|(\b\d{4}\b|[,\s])+)?)",  # dates
                line)
            author = re.match(r"(?si)(a|au|aut[hors]*):(?P<c>.*)", line)
            journal = re.match(
                r"(?si)(j|jo|jou[rnal]*|s|so|sou[rce]|jr*):(?P<c>.*)", line)
            title = re.match(r"(?si)(t|ti|tit[le]*):(?P<c>.*)", line)
            if date:
                lst.append(("date", date.group(2)))
            elif re.match(r"type:|ty:|\s*(not\s)?\s*(book|journal|proceeding)",
                          line):
                line = self._publicationType(line)
                if line:
                    lst.append(("type", line))
            elif author:
                author = author.group("c").strip()
                author = re.sub(r"(\w{2,},\s+\w)(?=\s|$)", r"\1*", author)
                lst.append(("author", author))
            elif journal:
                lst.append(("journal", journal.group("c").strip()))
            elif title:
                lst.append(("title", title.group("c").strip()))
            elif re.match(r"(any|all|^):", line):
                # all fields search
                lst.append(("all", re.sub(r".*?:\s*", "", line)))
            elif re.match(r"\w{2,3}:", line):
                # unrecognized field
                m = re.match(r"(?si)(\w{2,3}):\s*(.*)$", line)
                lst.append(m.group(1, 2))
            elif re.match(r"(?si)\s*\w+,\s+\w(\s|\*|$)", line):
                # author without field specification
                line = (line + '*').replace('**', '*')
                lst.append(("author", '"'+line+'"'))
            else:
                # something
                lst.append(("none", line))
        return lst

    def _publicationType(self, line):
        """
        Format type of the source according to zbMATH style.

        Publication types: journal/book/(book article=proceedings).
        """
        line = line.replace("type:", "").replace("ty:", "") \
            .replace("book article", "a") \
            .replace("proceeding", "a").replace("book", "b") \
            .replace("journal", "j").replace("s", "") \
            .replace("not", "!").replace("and", '|').replace("or", "|") \
            .replace("p", "a")
        line = re.sub(r"\s+", "", line)
        line = re.sub(r"[^abj|!&]", "", line)
        line = re.sub(r"\B", "|", line)
        if re.match("(!?[abj])([!|&][abj])?([!|&][abj])?$", line):
            # we have a zbl formatted type
            return line
        else:
            return ""

    def _formatQuery(self, query_dict):
        """
        Query formatting should be implemented in subclasses.

        The resulting format should be a string ready for URL inclusion.

        Each field in query_dict is a list of strings.
        """
        pass

    def _processResults(self, data):
        """
        Result processing should be implemented in subclasses.

        Valid BibTex entries must be placed in self.refs.
        Number of records should be placed in self.number.
        """
        pass

    def getRefs(self, **format_dict):
        """
        Return the list of fetched and formatted references.

        Run BibTex if necessary.
        """
        # nonexistent key get value "" (also evaluates to False)
        dct = defaultdict(str)
        try:
            dct.update(format_dict)
        except:
            pass
        if dct["bibtexOut"]:
            return self.refs
        if self.bibitem and dct["keepBibitems"]:
            # bibitem exists and should be kept, so do not generate
            dct["genBibitems"] = False
        if not dct["keepBibitems"] or dct["genBibitems"]:
            # remove saved bibitem if should be generated or not kept
            self.bibitem = ""
        return self._processBibTex(dct)

    def _processBibTex(self, format_dict):
        """
        Execute BibTex with options taken from format dictionary.

        Returns formatted string with citations.
        """
        try:
            bib = BibTex(**format_dict)
            formatted = bib.run(self.refs)
            assert formatted is not ""

            formatted = self.bibitem + formatted
            return formatted

        except:
            # bibtex failed, return unformatted bibtex entries
            return self.refs

    def _cleanupBibTex(self, count):
        """ Clean up bibtex and ensure uniform look. """
        import bibtexparser
        from bibtexparser.bparser import BibTexParser
        parser = BibTexParser()
        parser.customization = homogeneize_latex_encoding
        bib = bibtexparser.loads(self.refs, parser=parser)

        # save results
        from bibtexparser.bwriter import BibTexWriter
        writer = BibTexWriter()
        writer.contents = ['entries']
        writer.indent = '    '
        writer.order_entries_by = ('id')
        self.number = len(bib.entries)
        self.refs = bibtexparser.dumps(bib, writer)

    def setBibtex(self, bibstr):
        """
        Use ready bibtex string in the fetcher.

        Can be used to get formatted references out of the fetcher.
        """
        bibstr = fixQuery(bibstr)
        self.refs = str(bibstr)
        self._cleanupBibTex(None)


def fixQuery(query):
    """ Turn unicode or str into nice str. """
    try:
        if isinstance(query, str):
            # string may be encoded
            # should probably assume utf-8
            # but assume Eastern Europe :)
            query = unicode(query, 'cp1250')
            # Polish \l may end up as the below characters
            query = query.replace(u"\xc2\u0142", "l") \
                .replace(u"\xc2\u0141", "L")
        # eliminate all strange characters
        # again handle Polish \l
        # query better be unicode by now
        query = unicodedata.normalize('NFKD', query) \
            .replace(u'\u0141', 'L').replace(u'\u0142', 'l') \
            .encode('ascii', 'ignore')
    except:
        # what to do?
        query = unicode(query, errors='ignore')
    return query


# modified bibtexparser.latexenc content

from bibtexparser.latexenc import protect_uppercase, unicode_to_latex_map


def string_to_latex(string):
    """ Convert a string to its latex equivalent. """
    escape = [' ', '{', '}']

    new = []
    for char in string:
        if char in escape or ord(char) < 128:
            new.append(char)
        else:
            new.append(unicode_to_latex_map.get(char, char))
    return ''.join(new)


def homogeneize_latex_encoding(record):
    """ Replace accents with latex equivalents. """
    for val in record:
        if val not in ('ID',):
            record[val] = string_to_latex(record[val])
            if val == 'title':
                record[val] = protect_uppercase(record[val])
    return record
