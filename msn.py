"""MathSciNet fetching classes."""

from fetch import Fetch
import re

types = {'ref': 'REFF', 'ic': 'IC', 'se': 'SE', 'rt': 'RT', 'mr': 'MR',
         'rev': 'RVCN', 'all': 'ALLF', 'any': 'ALLF', 'mscp': 'PC',
         'pc': 'PC', 'cc': 'CC', 'msc': 'cc', 'ar': 'ICN', 'rel': 'ICN',
         'icn': 'ICN', 'title': 'TI', 'author': 'AUCN', 'journal': 'JOUR',
         'none': 'ALLF', 'type': 'ET', 'aid': 'INDI'}


class MathSciNet(Fetch):

    """ MathSciNet fetching class. """

    url = ("http://www.ams.org/mathscinet/search/publications.html?"
           "fmt=bibtex&extend=1&")
    website = ("http://www.ams.org/mathscinet/search/publications.html?"
               "fmt=hl&extend=1&")
    more = "r="
    correction = 1
    onceMax = 100

    def _preprocessQuery(self, query):
        """ Catch MR number query or execute regular preprocessing. """
        match = re.search(
            r"(?si)(mr:?|\\mref\s*\{|mrnumber\s*=\s*\{)\s*(mr)?\d{6,}",
            query)
        if match:
            return [("mr", ' or '.join(re.findall(r"\d{6,}", query)))]
        else:
            return super(MathSciNet, self)._preprocessQuery(query)

    def _formatQuery(self, lst):
        """ Turn query into a string accepted by MathSciNet. """
        # form query string
        lst = self._adjustList(lst)
        query = []
        cell = 1
        for key, value, logic in lst:
            if cell > 10:
                # too many lines
                break
            if re.match(r"\W*$", value):
                # empty line
                continue
            if key in {"mr", "mrnumber", "id"}:
                return [("pg1", "MR"), ("co1", "AND"), ("s1", value)]
            elif key == "type":
                value = value[0].replace("a", "Proceedings") \
                    .replace("b", "Books").replace("j", "Journals")
            if key.lower() in types:
                key = types[key.lower()]
            else:
                key = key.upper()
            if key == "DATE":
                query += self._formatDate(value)
            elif key in types.values():
                query += self._formatGeneric(key, value, logic, cell)
                cell += 1
        return query

    def _adjustList(self, lst):
        """ Extract logical connectors and forget parentheses. """
        if lst[0]:
            # normal field, value pairs
            lst = [(e[0], e[1], 'AND') for e in lst]
        else:
            # fields with logical connector and parentheses
            # but no parentheses between MSN fields
            logic = re.compile(r"(?si)(and|or|not)?[\s()\n]*$")
            # connectors: find last and/or/not (and not will work too)
            con = [logic.search(e).group(1) for e in lst[3::2]] + ['and']
            con = [(e if e else 'and').upper() for e in con]
            # fields
            lst = [e for e in lst[2::2] if len(e) > 1]
            # add missing parentheses
            lst = [(k, v + ")"*(v.count('(')-v.count(')'))) for k, v in lst]
            lst = zip(con, lst)
            # list (field, value, connector)
            lst = [(e[1][0], e[1][1], e[0]) for e in lst]
        return lst

    def _formatGeneric(self, key, value, logic, cell):
        """
        Format a generic field.

        Words must have 'and' between them, otherwise they are considered
        as phrases. We use " " for phrases with optional 'and' connector,
        as on arXiv and zbMATH.
        """
        value = re.split(r'(?si)\s*"\s*', value.strip())
        for i in range(0, len(value), 2):
            # every other one is in " "
            value[i] = re.sub(r"\s+", " and ", value[i].strip())
        # join phrases with and
        value = " and ".join(value)
        # now too many and's
        value = re.sub(r"(and|\s)+or(and|\s)+", " or ", value)
        value = re.sub(r"(and|\s)+not(and|\s)+", " not ", value)
        value = re.sub(r"(and|\s)+and(and|\s)+", " and ", value)
        value = re.sub(r"^\s*(and|or)\s*|\s*(and|or|not)\s*$", "", value)
        sc = str(cell)
        return [("pg"+sc, key), ("co"+sc, logic), ("s"+sc, value)]

    def _formatDate(self, value):
        """ Format date and range for MSN. """
        m = re.match(r".*(\d{4})\s*-+\s*(\d{4})", value)
        if m:
            return [("dr", "pubyear"), ("yearRangeFirst", m.group(1)),
                    ("yearRangeSecond", m.group(2))]
        else:
            ineq, year = re.match(r"\s*([<=>])?\s*(\d{4})", value) \
                .group(1, 2)
            if ineq is None:
                ineq = '='
            ineq = ineq.replace('=', 'eq').replace('<', 'lt') \
                .replace('>', 'gt')
            return [("dr", "pubyear"), ("yrop", ineq), ("arg3", year)]

    def _processResults(self, data):
        try:
            data = re.match(r'(?si).*"doc">(.*)<div id="foot.*', data).group(1)
            data = ''.join(data.split('<pre>')[1:])
            data = re.sub(r'</?(div|pre)>', '', data)
            data = re.sub(r"(?mi)MRNUMBER\s*=\s*\{(.*?)(\s|\}).*",
                          r"MRNUMBER = {\1},", data)
            data = data.replace(r'&lt;', '<').replace(r'&gt;', '>') \
                .replace(r'&amp;', '&')
        except:
            data = ""
        self.refs = data

    def _cleanWebsite(self, data):
        """ Extract highlights from the website. """
        data = re.sub(r'(?si)^.*?<div class="headlineText">', '', data)
        data = re.sub(r'(?si)</form>.*', '', data)
        data = re.sub(r'(?si)<div class="sfx.*?</noscript>.*?</div>', '', data)
        data = re.sub(r'(?si)<div class="headlineMenu.*?</div>', '', data)
        data = re.sub(r'(?si)<div class="headline_dates.*?'
                      r'<div class="headlineText">', '</p><p>', data)
        data = re.sub(r'(?si)<div.*', '', data)
        data = re.sub(r'(?si)<a class="item_status.*?</a>', '&nbsp;', data)
        data = re.sub(r'(?si)\(Reviewer:.*?(?=<a\s)', '', data)
        data = re.sub(r'(?si)<a href=[^<]*?mscdoc[^/]*?</a>', '', data)
        data = re.sub(r'(?si)(class|title)="[^"]*"', '', data)
        # fix links
        data = re.sub(r'href="/math', 'href="http://www.ams.org/math', data)

        return unicode('<p>' + data + '</p>', encoding="utf-8", errors="ignore")


class MRef(Fetch):

    """
    MRef fetching class.

    Returns a unique result or nothing.
    """

    url = "http://www.ams.org/mathscinet-mref?dataType=bibtex&"

    def _preprocessQuery(self, query):
        """ Return almost full query without any preprocessing. """
        query = re.sub(r'(?si)\bEdited\s+by\b', ' ', query)
        return [('ref', query)]

    def _formatQuery(self, query):
        """ Pass the query straight to urlencode. """
        return query

    def _processResults(self, data):
        """ Try to get the only bibtex record present in the html document. """
        m = re.match(r'.*(?si)<pre>(.*?)</pre>', data)
        if m and m.group(1):
            data = m.group(1)
        else:
            data = ""
        data = re.sub(r"(?mi)MRNUMBER\s*=\s*\{(.*?)(\s|\}).*",
                      r"MRNUMBER = {\1},", data)
        data = data.replace(r'&lt;', '<').replace(r'&gt;', '>') \
            .replace(r'&amp;', '&')
        self.refs = data
