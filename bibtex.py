""" Class for handling BibTex interactions. """

from collections import defaultdict
from tempfile import NamedTemporaryFile as tempFile
import os
import re


# HTML formatting for LaTex commands
_HTML = {
    'emph': r'<font style="font-style:italic;font-weight:bold;">',
    'textit': r'<font style="font-style:italic;">',
    'textbf': r'<font style="font-weight:bold;">',
    'textsc': r'<font style="font-variant:small-caps;">',
}


class BibTex(object):

    """ Handles BibTex calls and postprocessing of results. """

    def __init__(self, **format_dct):
        """
        Adjust bst file based on dct dictionary.

        dct should hold formatting directives.
        """
        ddct = defaultdict(str)
        ddct.update(format_dct)
        bst = tempFile(delete=False, suffix='.bst')
        self.name = os.path.splitext(bst.name)[0]
        self.shortname = os.path.split(self.name)[1]
        self.path = os.path.split(bst.name)[0]
        self.fdict = ddct
        with open(self.name + '.tex', 'w') as f:
            print >>f, r"""
                \documentclass{{article}}
                \begin{{document}}
                \nocite{{*}}
                \bibliographystyle{{{0}}}
                \bibliography{{{0}}}
                \end{{document}}""".format(self.shortname)

        path = os.path.dirname(os.path.realpath(__file__))
        with open(path + '/default.bst', 'r') as f:
            template = f.read()

        if ddct["query"]:
            template = re.sub(r"\{f.~\}\{vv~\}\{ll\}\{, jj\}", "{ll}", template)
            self.reverse = False
        else:
            template = self.adjustBst(ddct, format_dct, template)
        print >>bst, template
        bst.close()

    def adjustBst(self, ddct, format_dct, template):
        """ Adjust bst file to the format given by format_dct. """
        # put style commands in template
        for key, value in format_dct.items():
            m = re.match('(.*)Style', key)
            if not m or value is None or value == "None":
                continue
            key = m.group(1)
            if not re.search(r'(?s)---' + key + 'style---', template):
                continue
            start = re.sub(r'\W', '', value)
            end = ""
            if start:
                if ddct["html"]:
                    # these will be replaced with HTML code later
                    # BibTex would not like the HTML code
                    end = "end_html_" + start + "_end}"
                    start = r"\\" + start + "{start_html_" + start + "_start"
                else:
                    end = '}'
                    start = r'\\' + start + '{'
            template = re.sub("(?s)---"+key+"style---", start, template)
            template = re.sub("(?s)---"+key+"styleend---", end, template)

        # remove remaining styled places
        template = re.sub(r"(?si)---\w+?style---", "", template)
        template = re.sub(r"(?si)---\w+?styleend---", "", template)

        # sorting
        if 'name' in ddct["sortBy"]:
            template = re.sub(r"presort3", r"presort2", template)
            self.reverse = False
        else:
            self.reverse = 'oldest' not in ddct['sortBy']

        # generate bibitem
        if ddct["genBibitems"]:
            bibitem = ddct["bibitemStyle"]
            # uncomment bibitem
            template = template.replace(r"% ", "")
            if "{id}" in bibitem:
                # {id}
                template = template.replace(r"%%id", "")
            else:
                # {initialsyear}
                template = template.replace(r"%%initials", "")
            if '[' in bibitem:
                # [initialsyear]
                template = template.replace(r"%%[]", "")

        return template

    def run(self, bibstr):
        """Execute BibTex with entries from bibstr, and retrieve the results."""
        with open(self.name + '.bib', 'w') as f:
            print >>f, bibstr
        try:
            os.system('cd {}; pdflatex -interaction=batchmode {} >/dev/null'
                      .format(self.path, self.shortname))
            os.system('cd {}; bibtex {} >/dev/null'
                      .format(self.path, self.shortname))
            with open(self.name + '.bbl', 'r') as f:
                data = f.read()
            self.cleanup('blg', 'aux', 'bib', 'log', 'bbl')
        except:
            self.cleanup('blg', 'aux', 'bib', 'log', 'bbl')
            return ""
        # postprocess data
        data = re.sub(r"^[\n\r\s]*", "", data)
        data = re.sub(r"(?<=[^\n])\n", " ", data)
        data = re.sub(r" +", " ", data)
        data = re.sub(r"\n", "\n\n", data)

        if self.reverse:
            data = '\n\n'.join(data.split('\n\n')[::-1])

        # put HTML code
        for key, value in _HTML.items():
            data = re.sub("(?s)start_html_" + key + "_start", value, data)
            data = re.sub("(?s)end_html_" + key + "_end", "</font>", data)

        # handle conditional numbers

        data = "\n\n".join([self.removeNumbers(d) for d in data.split("\n\n")])
        data = re.sub(r"[A-Z]{2,3}_END", "}", data) \
            .replace("MR_START", r"\mref{MR").replace("AR_START", r"\arxiv{") \
            .replace("ZBL_START", r"\zbl{").replace("DOI_START", r"\doi{") \
            .replace("URL_START", r"\url{")

        # cleanup data
        data = re.sub(r"(?s)start_html_(\w+)_start", "", data)
        data = re.sub(r"(?s)end_html_(\w+)_end", "", data)
        data = re.sub(r"(?s)\\cprime", r"$'$", data)
        data = re.sub(r"(?s)\\(bold|Bbb)", r"\bf", data)
        data = re.sub(r"\{([A-Z])\}", r"\1", data)

        return data

    def removeNumbers(self, data):
        """ Remove unwanted numbers. """
        d = self.fdict
        p = d["type"]  # search or batch?

        # FIXME check this actually works

        # MR and Zbl
        mrzbl = {'Both': [True, True], 'MR#': [True, False],
                 'Zbl#': [False, True], 'Neither': [False, False]}
        try:
            # absolute
            keep = mrzbl[d[p+"MRZbl"]]
            if not keep[0]:
                data = re.sub(r'(?si)MR_START.*?MR_END', '', data)
            if not keep[1]:
                data = re.sub(r'(?si)ZBL_START.*?ZBL_END', '', data)
        except:
            # conditional
            if re.search("MR_START", data) and 'Zbl# if' in d[p+"MRZbl"]:
                data = re.sub(r'(?si)ZBL_START.*?ZBL_END', '', data)
            if re.search("ZBL_START", data) and 'MR# if' in d[p+"MRZbl"]:
                data = re.sub(r'(?si)ZBL_START.*?ZBL_END', '', data)
        # arxiv
        if d[p+"Arxiv"] == 'Exclude':
                data = re.sub(r'(?si)AR_START.*?AR_END', '', data)
        # doi/link
        something = not not re.search(r'(?si)(MR|ZBL|AR)_START', data)
        mrorzbl = not not re.search(r'(?si)(MR|ZBL)_START', data)
        doi = d[p+"IncludeDOIURL"]
        if doi == 'Exclude' or ('arXiv' in doi and something) or \
                ('Only' in doi and 'arXiv' not in doi and mrorzbl):
            # remove doi and link
            data = re.sub(r'(?si)DOI_START.*?DOI_END', '', data)
            data = re.sub(r'(?si)URL_START.*?URL_END', '', data)
        # doi or link?
        doi = d[p+"DOIURL"]
        if doi == 'URL':
            data = re.sub(r'(?si)DOI_START.*?DOI_END', '', data)
        elif doi == 'DOI#' or ('different' in doi and re.search(
                r"(?si)URL_START[^\s\n]*?dx\.doi[^\s\n]*?URL_END", data)):
            data = re.sub(r'(?si)(URL_START.*?URL_END)', '', data)
        elif 'as' in doi:
            doi = re.search(r'(?si)DOI_START(.*?)DOI_END', data)
            if doi and doi.group(1):
                # DOI exists, but should look like URL
                data = re.sub(r'(?si)(URL_START).*?(URL_END)',
                              r'\1http://dx.doi.org/{}\2'.format(doi.group(1)),
                              data)
                # remove DOI
                data = re.sub(r'(?si)DOI_START.*?DOI_END', '', data)
        return data

    def cleanup(self, *args):
        """ Remove temporary files. """
        for l in args:
            try:
                os.unlink(self.name + '.' + l)
            except:
                pass

    def __del__(self):
        """ Remove remaining temporary files. """
        try:
            self.cleanup('tex', 'bst')
        except:
            pass
