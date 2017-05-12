# -*- coding: utf-8 -*-
"""This module is used to load all RDF Namespaces.

Use: from namespaces import *
"""

from rdflib import Namespace

RDF     = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
RDFS    = Namespace("http://www.w3.org/2000/01/rdf-schema#")
OWL     = Namespace("http://www.w3.org/2002/07/owl#")
XSD     = Namespace("http://www.w3.org/2001/XMLSchema#")

OBO2    = Namespace("http://purl.obolibrary.org/obo#")
SKOS    = Namespace("http://www.w3.org/2004/02/skos/core#")
DCT     = Namespace("http://purl.org/dc/terms/")
DOAP    = Namespace("http://usefulinc.com/ns/doap#")
CYC     = Namespace("http://biocyc.org/")

MCYC    = Namespace("http://metacyc.org/")
CHEBI   = Namespace("http://purl.obolibrary.org/obo/CHEBI/")
KEGG    = Namespace("http://www.genome.jp/linkdb/")
BIGG    = Namespace("http://bigg.ucsd.edu/")
MNX     = Namespace("http://metanetx.org/")
BP      = Namespace("http://www.biopax.org/release/biopax-level3.owl#")
MNXBP   = Namespace("http://metanetx.org/biopax/biopax-level3#")

DYL     = Namespace("http://www.irisa.fr/dyliss/")
DYLDATA = Namespace("http://www.irisa.fr/dyliss/data/")
DYLMETA = Namespace("http://www.irisa.fr/dyliss/metadata/")
DYLMAP  = Namespace("http://www.irisa.fr/dyliss/mappings/")


def get_RDF_prefixes():
    """Prefixes sent in SPARQL queries.

    """

    return """
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    PREFIX obo2: <http://purl.obolibrary.org/obo#>

    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
    PREFIX dct: <http://purl.org/dc/terms/>
    PREFIX doap: <http://usefulinc.com/ns/doap#>

    PREFIX cyc: <http://biocyc.org/>
    PREFIX mcyc: <http://metacyc.org/>
    PREFIX chebi: <http://purl.obolibrary.org/obo/CHEBI/>
    PREFIX kegg: <http://www.genome.jp/linkdb/>
    PREFIX mnx: <http://metanetx.org/>
    PREFIX bigg: <http://bigg.ucsd.edu/>

    PREFIX dyl: <http://www.irisa.fr/dyliss/>
    PREFIX dyldata: <http://www.irisa.fr/dyliss/data/>
    PREFIX dylmeta: <http://www.irisa.fr/dyliss/metadata/>
    PREFIX dylmap: <http://www.irisa.fr/dyliss/mappings/>

    """


