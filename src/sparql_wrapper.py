# -*- coding: utf-8 -*-
"""Module used to query SPARQL endpoint.

"""

from src.commons import SPARQL_PATH

try:
    from SPARQLWrapper import SPARQLWrapper, JSON
except ImportError:
    raise ImportError("SPARQLWrapper seems not to be installed. \
          Please install the module with the following command:\n \
          sudo pip install SPARQLWrapper \n \
          or \
          pip install --user SPARQLWrapper")

# Custom imports
#from rdfstore import commons as cm
from src import namespaces as nm

# TODO revoir le json avec sparqlwrapper2
def auto_add_prefixes(func):
    """Decorator: Add all prefixes to the SPARQL query at first argument
    of sparql_query()
    """

    def fonction_modifiee(*args, **kwargs):
        return func(nm.get_RDF_prefixes() + args[0], **kwargs)

    return fonction_modifiee


def load_sparql_endpoint():
    """Make a connection to SPARQL endpoint & retrieve a cursor.

    :return: sparql cursor in version 2!
             => this cursor is made for servers that return JSON by default !
    :rtype: <SPARQLWrapper2>

    """

    return SPARQLWrapper(SPARQL_PATH, 'POST') # CHECK THIS


@auto_add_prefixes
def sparql_query(query):
    """Wait for a valid database URI, and a SPARQL query.
    Yields all triplets returned by the query.
    The query need to yield three values, named object, relation and subject.

    .. warning:: SPARQLWrapper2: http://rdflib.github.io/sparqlwrapper/doc/latest/
              with SPARQLWrapper2, server must return JSON data !
              if not, please use SPARQLWrapper:
              sparql.setReturnFormat(SPARQLWrapper.JSON)
              followed by: sparql.queryAndConvert()
    """

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
    except Exception as e:
        print("SPARQL query error" + str(e))
        raise

    for binding in results['results']['bindings']:
        yield tuple(binding.get(var, dict()).get('value', None)
                    for var in results['head']['vars'])


def get_all_names():
    """Get all entities with names in graph"""

    query = """
	PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
	PREFIX biopax3: <http://www.biopax.org/release/biopax-level3.owl#>

	SELECT DISTINCT ?pathway ?pathwayname 
	WHERE 
	{
		?pathway rdf:type biopax3:Pathway .
		?pathway biopax3:displayName ?pathwayname 
	}
	LIMIT 100
    """

    for tab in sparql_query(query): print("ORIG:   ", tab)


if __name__ == "__main__":
    get_all_names()

