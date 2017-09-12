# -*- coding: utf-8 -*-
# MIT License
#
# Copyright (c) 2017 IRISA, Jean Coquet, Pierre Vignet, Mateo Boudet
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Contributor(s): Jean Coquet, Pierre Vignet, Mateo Boudet

"""Module used to query SPARQL endpoint.

"""
from __future__ import print_function

# Standard imports
import itertools as it
try:
    from SPARQLWrapper import SPARQLWrapper, JSON
except ImportError:
    raise ImportError("SPARQLWrapper seems not to be installed. \
          Please install the module with the following command:\n \
          sudo pip install SPARQLWrapper \n \
          or \
          pip install --user SPARQLWrapper")

# Custom imports
from biopax2cadbiom import namespaces as nm
import biopax2cadbiom.commons as cm

LOGGER = cm.logger()


def auto_add_prefixes(func):
    """Decorator: Add all prefixes to the SPARQL query at first argument
    of sparql_query()
    """

    def fonction_modifiee(*args, **kwargs):
        return func(nm.get_RDF_prefixes() + args[0], **kwargs)

    return fonction_modifiee


def order_results(query, orderby='?uri', limit=9999):
    """Build nested query for access points with restrictions.

    Build the nested query by encapsulate the original between
    the same SELECT command (minus useless DISTINCT clause),
    and the OFFSET & LIMIT clauses at the end.
    PS: don't forget to add the ORDER BY at the end of the original query.

    http://vos.openlinksw.com/owiki/wiki/VOS/VirtTipsAndTricksHowToHandleBandwidthLimitExceed
    https://etl.linkedpipes.com/components/e-sparqlendpointselectscrollablecursor

    .. warning:: WE ASSUME THAT THE SECOND LINE OF THE QUERY CONTAINS THE FULL
        SELECT COMMAND !!!

    :param arg1: Original normal SPARQL query.
    :param arg2: Order queries by this variable.
    :param arg3: Max items queried for 1 block.
    :type arg1: <str>
    :type arg2: <str>
    :type arg3: <int>
    :return: A generator of lines of results.
    :rtype: <dict>
    """

    # Assume that the second line contains the SELECT command
    second_query_line = query.split('\n')[1]
    assert 'SELECT' in second_query_line

    # Build the nested query by encapsulate the original between
    # the same SELECT command (minus useless DISTINCT clause),
    # and the OFFSET & LIMIT clauses at the end.
    # PS: don't forget to add the ORDER BY at the end of the original query.
    query_prefix = query.split('\n')[1].replace('DISTINCT', '') + '\nWHERE { '

    for offset in it.count():

        query_suffix = """
                ORDER BY """ + orderby + """
            }
            OFFSET """ + str(limit * offset) + """
            LIMIT """ + str(limit)

        # Begin from 1 (avoid to break at limit-1 later)
        count = 1 # No result in the query => count not initialized
        for count, result in enumerate(
            sparql_query(query_prefix + query + query_suffix), 1
        ):
            # print(result, offset, count)
            yield result

        # The last block size is less than limit => we stop iteration
        if count < limit:
            break


def load_sparql_endpoint():
    """Make a connection to SPARQL endpoint & retrieve a cursor.

    :return: sparql cursor in version 1!
        => we don't use SPARQLWrapper2 cursor that provides
        SPARQLWrapper.SmartWrapper.Bindings-class to convert JSON from server.
    :rtype: <SPARQLWrapper>

    """

    return SPARQLWrapper(cm.SPARQL_PATH, 'POST') # CHECK THIS


@auto_add_prefixes
def sparql_query(query):
    """Wait for a valid database URI, and a SPARQL query.
    Yields all triplets returned by the query.
    The query need to yield three values, named object, relation and subject.

    :param: SPARQL query
    :type: <str>
    :return: Generator of results.
    :rtype: <generator <tuple>>
    """

    LOGGER.debug(query)
    sparql = load_sparql_endpoint()

    # data in JSON format => proper python dict()
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)

    try:
        # PS: if XML stream is not used: don't use sparql.query(),
        #but sparql.queryAndConvert() instead.
        results = sparql.queryAndConvert()

        # Dictionary of dictionnaries in result
        # ex:
        # {
        #  "head": {
        #    "vars": [ "METACYC" , "name" ]
        #  } ,
        #  "results": {
        #    "bindings": [
        #      {
        #        "METACYC": { "type": "literal" , "value": "PROPANOL" }
        #      }
        #    ]
        #  }
        # }
#        print(results)
#        print("results: ", len(results['results']['bindings']))
    except Exception as e:
        print("SPARQL query error" + str(e))
        raise

    for binding in results['results']['bindings']:
        yield tuple(binding.get(var, dict()).get('value', None)
                    for var in results['head']['vars'])
