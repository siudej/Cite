""" Zentralblatt fetching classes. """

from fetch import Fetch
import re
import urllib

types = {'title': 'ti', 'author': 'au', 'pu': 'pu', 'msc': 'cc',
         'journal': 'so', 'la': 'la', 'none': 'any', 'type': 'dt',
         'id': 'an', 'zbl': 'an'}


class Zbl(Fetch):

    """ zbMATH fetching class. """

    url = "http://zbmath.org/?"
    more = ""

    def _preprocessQuery(self, query):
        """ Catch Zbl number query or execute regular preprocessing. """
        match = re.search(
            r"(?si)(zbl:|zbmath:?|\\zbl\s*\{|zbl\s*=\s*\{)\s*(zbl|zbmath)?"
            r"\d{4}\.?\d{4,}",
            query)
        if match:
            return [("zbl",
                     ' or '.join(re.findall(r"\b\d{4}\.?\d{4,}\b", query)))]
        else:
            return super(Zbl, self)._preprocessQuery(query)

    def _formatQuery(self, lst):
        """
        Turn query into a urlencode ready dictionary accepted by zbMATH.

        zbMATH is using |&! as logical connectors.
        There is something strange with in the way ! behaves.

        If a field (line) has matching parentheses we wrap the field in ().
        This allows for queries like: a and (b or c) in a field.
        """
        query = ""
        for e in lst:
            try:
                # parentheses and logic between fields
                query += e.replace('and', '&').replace('or', '|') \
                    .replace('not', '!')
            except:
                # field
                key, value = e
                key = key.lower()
                if not key:
                    query += value.replace('and', '&').replace('or', '|') \
                        .replace('not', '!')
                    continue
                if key in types:
                    key = types[key]
                if key == "date":
                    fromto = re.match(r"(\d{4})\s*-+\s*(\d{4})", value)
                    years = re.findall(r"\d{4}", value)
                    ineq = re.search(r"[<>]\s*(\d{4})", value)
                    if fromto:
                        # range works
                        query += " py: {0}-{1} ".format(*fromto.group(1, 2))
                    elif len(years) > 1 or not ineq:
                        # many years listed
                        query += " py: " + '|'.join(years) + " "
                    elif ">" in value:
                        # year above by range
                        start = int(ineq.group(1))
                        query += " py: {0}-{1} ".format(start+1, 3000)
                    else:
                        # year below by range
                        end = int(ineq.group(1))
                        query += " py: {0}-{1} ".format(1000, end-1)
                elif key in types.values():
                    value = value.replace(' and ', ' & ').replace(' or ', '|') \
                        .replace(' not ', ' ! ').replace('Illinois', 'Ill*')
                    query += " {0}: {1} ".format(key, value)
        query = re.sub(r"[\n\s]+", " ", query).strip()
        return [('q', query)]

    def _processResults(self, data):
        """ Get bibtex data from zbMATH website. """
        bibs = re.findall("(?si)bibtex/.*?\d{3,}\.bib", data)
        data = []
        import bibtexparser
        from bibtexparser.bparser import BibTexParser
        parser = BibTexParser()
        parser.customization = customizations
        if self.otherID:
            # setup for MRef fetching
            from msn import MRef
            mr = MRef()
        for bib in bibs:
            bibtext = urllib.urlopen("https://zbmath.org/" + bib).read()
            zbl = bibtexparser.loads(bibtext, parser=parser)
            if self.otherID and mr.fetch(bibtext):
                # found MRef match for zbMATH record
                msn = bibtexparser.loads(mr.refs)
                # use MSN bibtex entry with zbl number added
                # and doi transfered if missing
                msn.entries[0]['zbl'] = zbl.entries[0]['zbl']
                if 'doi' not in msn.entries[0] and 'doi' in zbl.entries[0]:
                    msn.entries[0]['doi'] = zbl.entries[0]['doi']
                zbl = msn
            data.append(bibtexparser.dumps(zbl))
        self.refs = "\n".join(data)


def customizations(record):
    """ Modify zbl BibTex entries. """
    try:
        record["id"]
        ID = "id"
    except:
        ID = "ID"
    try:
        record[ID] = 'Zbl' + record["zbl"]
    except:
        record["zbl"] = record[ID].replace("zbMATH", "")
        record[ID] = 'Zbl' + record["zbl"]
    try:
        # put authors in last, first form
        n = 3  # match braces n levels deep
        authors = str(record["author"]).split(' and ')
        fixed = []
        for author in authors:
            m = re.match("(?si)(.*?)\{(" + r"[^{}]*?(?:\{"*n +
                         r"[^{}]*?"+r"\}[^{}]*?)*?"*n + r")\}$", author)
            fixed.append(m.group(2).strip() + ', ' +
                         re.sub(r'\.(\w\.)', r'. \1', m.group(1).strip()))
        record["author"] = " and ".join(fixed)
    except:
        pass
    return record
