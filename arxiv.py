""" Arxiv fetching class. """


from fetch import Fetch
import re
# import feedparser

types = {'title': 'ti', 'author': 'au', 'abs': 'ab', 'msc': 'soc',
         'journal': 'jr', 'doi': 'doi', 'cat': 'cat', 'none': '', 'co': 'co'}


class ArXiv(Fetch):

    """
    Arxiv fetching class.

    Uses UCDavis front.

    """

    url = "http://front.math.ucdavis.edu/search?n=200&"
    website = "http://front.math.ucdavis.edu/search?n=200&"
    more = ""

    def _preprocessQuery(self, query):
        """ Catch arxiv number query or execute regular preprocessing. """
        match = re.search(
            r"(?si)(arxiv:|\\arxiv\s*\{|arxiv\s*=\s*\{)\s*\d{4}\.\d{4,5}",
            query)
        if match:
            # extract as many IDs as possible
            # except that more than about 10 will not work
            # so make sure unique
            ids = list(set(re.findall(r"\d{4}\.\d{4,5}(?:v\d)?", query)))
            return [("id", '[' + ' '.join(ids[:10]) + ']')]
        else:
            return super(ArXiv, self)._preprocessQuery(query)

    def _formatQuery(self, lst):
        """
        Turn query into urlencode ready dictionary accepted by arxiv.

        and/or/not start new field
        [ list ] puts or between words in a field

        If a field (line) has matching parentheses we wrap the field in ().
        This allows for queries like: a and (b or c) in a field.
        """
        query = ""
        for e in lst:
            try:
                # parentheses and logic between fields
                query += e
            except:
                key, value = e
                key = key.lower()
                # field
                if not key:
                    query += value
                    continue
                if key in ('id', 'arxiv'):
                    return [('q', "id: (" + value + ")")]
                elif key == 'author':
                    value = re.sub(r"\b(\w+)\s*,\s*(\w)\b\*?", r"\1-\2", value)
                if key in types:
                    key = types[key]
                if key == "date":
                    query += self._formatDate(value)
                elif key in types.values():
                    # splitting may have removed a few parentheses for the value
                    # wrapping with () ensures field is enclosed
                    # putting back together restores missing parentheses
                    value = "(" + value + ")"
                    if key:
                        query += "{0}: {1} ".format(key, value)
                    else:
                        # start new field for a general query
                        query += "and {1} ".format(key, value)
        query = re.sub(r"[\n\s]+", " ", query).strip()
        return [('q', query)]

    def _formatDate(self, value):
        fromto = re.match(r"(\d{4})\s*-+\s*(\d{4})", value)
        years = re.findall(r"\d{4}", value)
        ineq = re.search(r"[<>]\s*(\d{4})", value)
        if fromto:
            # range by listing all years
            start, end = [int(e) for e in fromto.group(1, 2)]
            return " date:" + str(range(start, end + 1)) + " "
        elif len(years) > 1 or not ineq:
            # many years listed
            return " date:" + str(years) + " "
        elif ">" in value:
            # year above by listing
            start = int(ineq.group(1))
            return " date:" + str(range(start+1, start+21)) + " "
        else:
            # year below by listing
            end = int(ineq.group(1))
            return " date:" + str(range(end-20, end)) + " "

    def _processResults(self, data):
        """ Get bibtex data from arxiv html. """
        if re.match("(?si).*<title>Front: Not found</title>.*", data):
            self.refs = ""
            return
        data = re.sub(r'(?si).*?<table class="listing">', "", data, 1)
        data = re.sub(r'(?si)<p class="fromto">.*', "", data)
        data = data.split(r'<table class="listing">')
        self.refs = []
        for d in data:
            m = re.match(
                r'(?si).*href="/([^"]+).*?<b>(.*?)\s*\.\s*</b>(\n|\s)*(.*)', d)
            arxiv, title, authors = m.group(1, 2, 4)
            authors = re.sub(r'(?si)((.*)author.*?)</a>.*', r'\1', authors)
            # remove (...) sometimes appearing in authors
            authors = re.sub(r'\(\w+\)', '', authors)
            authors = re.split('</a>\s*,?\s*', authors)
            authors = [', '.join(re.split('\s*<.*>', a)[::-1]) for a in authors]
            d = """
            @unpublished{{{2},
                    author = {{{0}}},
                    title = {{{{{1}}}}},
                    arxiv = {{{2}}},
            }}""".format(' and '.join(authors), title, arxiv)
            self.refs.append(d)
        self.refs = '\n'.join(self.refs)
        self.refs = self.refs.replace(r'&lt;', '<').replace(r'&gt;', '>') \
            .replace(r'&amp;', '&')

    def _cleanWebsite(self, data):
        """ Extract highlights from the website. """
        data = re.sub(r'(?si)^.*?(?=<table class="listing)', '', data)
        data = re.sub(r'(?si)<p class="fromto.*$', '', data)
        data = re.sub(r'(?si)<table class="listing.*?<td class="text">',
                      '<p>', data)
        data = re.sub(r'(?si)</td.*?</table>', '</p>', data)
        data = re.sub(r'(?si)\(?<a href="/(math|phys).*?</p>', '</p>', data)
        # switch title and author
        data = re.sub(r'(?si)(<b>.*?</b>)(.*?)</p>', r'\2\1</p>', data)
        # fix links
        data = re.sub(r'(?si)href="/', 'href="http://front.math.ucdavis.edu/',
                      data)
        return unicode(data, encoding="utf-8", errors="ignore")
