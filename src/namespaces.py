# -*- coding: utf-8 -*-
"""This module is used to load all RDF Namespaces.

Use: from namespaces import *
"""

def get_RDF_prefixes():
    """Prefixes sent in SPARQL queries.

    """

    return """
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX biopax3: <http://www.biopax.org/release/biopax-level3.owl#>
    PREFIX XMLSchema: <http://www.w3.org/2001/XMLSchema#>
    """


