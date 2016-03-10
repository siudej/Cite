""" Tools for fetching multiple records from multiple sources. """

from msn import MathSciNet, MRef
from zbl import Zbl
from arxiv import ArXiv
from fetch import fixQuery
import re
from collections import defaultdict


class Batch(object):

    """
    Helper class for running multiple fetchers to get a unique match.

    Run MRef first. If successful, try to get Zbl number for it.
    If no result run Zbl. If unique, run MRef to get MR.
    If not unique, cache and run MathSciNet/MRLookup.
    If that one is unique, try to get Zbl number for it.
    If neither one was unique, merge and return all records.
    If nothing was found up to this point run arXiv.

    BibTex records are taken from MathSciNet if possible, with Zbl number added.

    As an option, run arXiv before others and return its result if unique.
    As another option, do not try to find zbl, or mr, when unique match found.
    """

    def __call__(self, query, count, dct):
        """ Imitate __call__ function from Fetch. """
        query = fixQuery(query)
        d = defaultdict(str)
        d.update(dct)
        dct = d
        # TODO start with arxiv?
        bibs = ""
        mref = MRef()
        mref.fetch(query, count)
        self.number = 1
        self.nonunique = False
        if mref.number:
            # MRef found a match
            return mref.refs, mref.getRefs(**dct)
        # now check Zbl
        if dct["batchFindMR"]:
            # run MRef too
            zbl = Zbl(otherID=True)
        else:
            zbl = Zbl()
        zbl.fetch(query, count)
        if zbl.number:
            # Zbl found something
            bibs = zbl.refs
            if not zbl.nonunique:
                # return only if unique match found
                return zbl.refs, zbl.getRefs(**dct)
        # now check MSN
        msn = MathSciNet()
        msn.fetch(query, count)
        if msn.number:
            # MSN found something
            if not msn.nonunique:
                # return only if unique match found
                return msn.refs, msn.getRefs(**dct)
            # combine msn and zbl records
            bibs += '\n\n' + msn.refs
        ar = ArXiv()
        ar.fetch(query, count)
        if ar.number:
            # arXiv found something
            if not ar.nonunique and not bibs:
                # return only if unique match found and nothing found so far
                return ar.refs, ar.getRefs(**dct)
            bibs += '\n\n' + ar.refs
        if bibs:
            # format and return combined records
            # this is a nonunique result
            msn.setBibtex(bibs)
            self.number = msn.number
            self.nonunique = True
            return msn.refs, msn.getRefs(**dct)
        # nothing was found, return the query
        self.number = 0
        self.nanunique = True
        return '', ''


def batchSplit(query, dct):
    """ Split query based on a chosen splitter. """
    # reomve comments
    query = re.sub(r'(?si)%.*?(?=\n|$)', '', query)
    splitters = {'bibitem': r'[\n\s]*(?=\\bibitem\s*[[{]|@\w+\s*\{)',
                 'empty': r'\n[\s\n]+',
                 'new': r'\n'
                 }
    splitter = splitters['bibitem']
    for i, s in splitters.items():
        if i in dct['separator']:
            splitter = s
            if i == 'bibitem':
                # if splitting on bibitems, keep bibitems
                dct['keepBibitems'] = True
    queries = [l for l in re.split(splitter, query)
               if not re.match(r'[\n\s]*$', l)]
    return queries, dct
