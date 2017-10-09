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

"""
This module contains a list of functions to query any SPARQL endpoint with
BIOPax data.
"""
from __future__ import unicode_literals

# Standard imports
from collections import defaultdict

# Custom imports
from biopax2cadbiom import sparql_wrapper
from classes import *


def getPathways(listOfGraphUri):
	pathwayToName = {}
	query = """
		SELECT DISTINCT ?pathway ?displayName
	"""
	for graphUri in listOfGraphUri:
		query += "FROM <"+graphUri+">\n"
	query += """
		WHERE
		{
			?pathway rdf:type biopax3:Pathway .
			OPTIONAL { ?pathway biopax3:displayName ?displayName . }
		}
	"""

	for pathway, name  in sparql_wrapper.order_results(
			query,
			orderby='?pathway'):

		if name is not None:
			pathwayToName[pathway] = name
		else:
			pathwayToName[pathway] = pathway

	return pathwayToName


def getPathwayAncestorsHierarchy(listOfGraphUri):
	query = """
		SELECT DISTINCT ?pathway ?superPathway
	"""
	for graphUri in listOfGraphUri:
		query += "FROM <"+graphUri+">\n"
	query += """
		WHERE
		{
			?superPathway rdf:type biopax3:Pathway .
			?superPathway biopax3:pathwayComponent ?pathway .
			?pathway rdf:type biopax3:Pathway .
			?pathway biopax3:pathwayComponent* ?subPathway .
			?subPathway rdf:type biopax3:Pathway .
		}
	"""

	pathwayToSuperPathways = defaultdict(set)
	for pathway, superPathway in sparql_wrapper.order_results(
			query,
			orderby='?pathway'):

		pathwayToSuperPathways[pathway].add(superPathway)

	return pathwayToSuperPathways


def getReactions(listOfGraphUri):
	"""
		.. warning:: si on fait 'rdfs:subClassOf* biopax3:Interaction'
		alors on recupere aussi les 'Control', ce qui est doit etre fait
		par getControls(listOfGraphUri)
	"""

	dictReaction = {}
	query = """
		SELECT DISTINCT ?reaction ?nameReaction ?reactionType ?pathway ?leftComponent ?rightComponent ?productComponent ?participantComponent
	"""
	for graphUri in listOfGraphUri:
		query += "FROM <"+graphUri+">\n"
	query += """
		WHERE
		{
			?reaction rdf:type ?reactionType .
			?reactionType rdfs:subClassOf* biopax3:Interaction .
			OPTIONAL { ?reaction biopax3:displayName ?nameReaction . }
			OPTIONAL { ?pathway biopax3:pathwayComponent ?reaction . }
			OPTIONAL {
				?reaction biopax3:left ?leftComponent .
				FILTER NOT EXISTS { ?leftComponent rdf:type biopax3:Pathway }
			}
			OPTIONAL {
				?reaction biopax3:right ?rightComponent .
				FILTER NOT EXISTS { ?rightComponent rdf:type biopax3:Pathway }
			}
			OPTIONAL {
				?reaction biopax3:product ?productComponent .
				FILTER NOT EXISTS { ?productComponent rdf:type biopax3:Pathway }
			}
			OPTIONAL {
				?reaction biopax3:participant ?participantComponent .
				FILTER NOT EXISTS { ?participantComponent rdf:type biopax3:Pathway }
			}
		}
	"""

	for reaction, \
		nameReaction, \
		reactionType, \
		pathway, \
		leftComponent, \
		rightComponent, \
		productComponent, \
		participantComponent in sparql_wrapper.order_results(
			query,
			orderby='?reaction'):

		if reaction not in dictReaction:
			dictReaction[reaction] = \
				Reaction(reaction, nameReaction,
						 reactionType, productComponent, participantComponent)
		if pathway is not None:
			dictReaction[reaction].pathways.add(pathway)
		if leftComponent is not None:
			dictReaction[reaction].leftComponents.add(leftComponent)
		if rightComponent is not None:
			dictReaction[reaction].rightComponents.add(rightComponent)

	return dictReaction


def getPhysicalEntities(listOfGraphUri):
	dictPhysicalEntity = {}
	query = """
		SELECT DISTINCT ?entity ?name ?synonym ?location ?type ?component ?member ?entityRef
	"""
	for graphUri in listOfGraphUri:
		query += "FROM <"+graphUri+">\n"
	query += """
		WHERE
		{
			?entity rdf:type ?type.
			?type rdfs:subClassOf* biopax3:PhysicalEntity.
			OPTIONAL { ?entity biopax3:displayName ?name . }
			OPTIONAL { ?entity biopax3:name ?synonym . }
			OPTIONAL { ?entity biopax3:cellularLocation ?location . }
			OPTIONAL { ?entity biopax3:component ?component . }
			OPTIONAL { ?entity biopax3:memberPhysicalEntity ?member . }
			OPTIONAL { ?entity biopax3:entityReference ?entityRef . }
		}
	"""

	def get_entity(entity_uri):

		try:
			# If present, return it
			return dictPhysicalEntity[entity_uri]
		except KeyError:
			# If not present, create it and the return it
			new_entity = \
				PhysicalEntity(entity_uri, name,
							   location, entityType, entityRef)

			dictPhysicalEntity[entity_uri] = new_entity
			return new_entity


	for entity_uri, \
		name, \
		synonym, \
		location, \
		entityType, \
		component_uri, \
		member, \
		entityRef in sparql_wrapper.order_results(query, orderby='?entity'):

		# Entity creation if not already met
		entity = get_entity(entity_uri)

		if synonym != None:
			entity.synonyms.add(synonym)

		if component_uri != None:
			# todo : reflechir à avoir 1 set de PhysicalEntity et non d'uri...
			# !!!!! le component hérite de par le fait des parametres de son parent là...
			# component = get_entity(component_uri)
			# entity.components.add(component)
			entity.components.add(component_uri)

		if member != None:
			entity.members.add(member)

	query = """
		SELECT DISTINCT ?entity ?dbRef ?idRef
	"""
	for graphUri in listOfGraphUri:
		query += "FROM <"+graphUri+">\n"
	query += """
		WHERE
		{
			?entity rdf:type ?type.
			?type rdfs:subClassOf* biopax3:PhysicalEntity.
			{
				{ ?entityRef biopax3:xref ?ref . }
				UNION
				{ ?entity biopax3:xref ?ref .}
			}
			?ref biopax3:db ?dbRef .
			?ref biopax3:id ?idRef .
		}
	"""

	for entity_uri, \
		dbRef, \
		idRef in sparql_wrapper.order_results(query, orderby='?entity'):

		entity.idRefs.add((idRef,dbRef))

	return dictPhysicalEntity


def getLocations(listOfGraphUri):
	dictLocation = {}
	query = """
		SELECT DISTINCT ?location ?locationTerm ?dbRef ?idRef
	"""
	for graphUri in listOfGraphUri:
		query += "FROM <"+graphUri+">\n"
	query += """
		WHERE
		{
			?entity biopax3:cellularLocation ?location .
			OPTIONAL { ?location biopax3:term ?locationTerm . }
			OPTIONAL {
				?location biopax3:xref ?ref .
				?ref biopax3:db ?dbRef .
				?ref biopax3:id ?idRef .
			}
		}
	"""

	for location, locationTerm, dbRef, idRef in sparql_wrapper.order_results(
		query,
		orderby='?location'):

		if location not in dictLocation:
			dictLocation[location] = Location(location, locationTerm)
		if idRef is not None:
			dictLocation[location].idRefs.add((idRef,dbRef))

	return dictLocation


def getControls(listOfGraphUri):
	"""

	.. note: controlType is in (ACTIVATION, INHIBITION)
	.. note: PID: Evidences nb: 15523, for controls nb: 8203
	"""

	dictControl = {}
	query = """
		SELECT DISTINCT ?control ?type ?controlType ?reaction ?controller ?evidence
	"""
	for graphUri in listOfGraphUri:
		query += "FROM <"+graphUri+">\n"
	query += """
		WHERE
		{
			?control rdf:type ?type.
			?type rdfs:subClassOf* biopax3:Control .
			?control biopax3:controlled ?reaction .
			?control biopax3:controlType ?controlType .
			?control biopax3:controller ?controller .
			OPTIONAL { ?control biopax3:evidence ?evidence . }
		}
	"""

	def get_entity(control_uri):

		try:
			# If present, return it
			return dictControl[control_uri]
		except KeyError:
			# If not present, create it and the return it
			new_control = \
				Control(control_uri, classType,
						controlType, reaction, controller)

			dictControl[control_uri] = new_control
			return new_control

	for control_uri, \
		classType, \
		controlType, \
		reaction, \
		controller, \
		evidence in sparql_wrapper.order_results(query, orderby='?control'):

		# Entity creation if not already met
		control = get_entity(control_uri)

		if evidence is not None:
			control.evidences.add(evidence)

	return dictControl


def get_xref_from_database(listOfGraphUri, database_name):
	"""Get corresponding xref from the given database name for all entities.

	.. note:: Each ontology can name its database differently.
		Ex: 'UniProt' vs 'uniprot knowledgebase', 'ChEBI' vs 'chebi'
	"""

	query = """
		SELECT DISTINCT ?entity ?idRef
	"""
	for graphUri in listOfGraphUri:
		query += "FROM <"+graphUri+">\n"
	query += """
		WHERE
		{
			?entity rdf:type ?type.
			?type rdfs:subClassOf* biopax3:PhysicalEntity.
			{
				{
					?entity biopax3:entityReference ?entityRef .
					?entityRef biopax3:xref ?ref .
				}
				UNION
				{
					?entity biopax3:entityReference ?entityRef .
					?entityRef biopax3:memberEntityReference ?memberEntityRef .
					?memberEntityRef biopax3:xref ?ref .
				}
				UNION
				{ ?entity biopax3:xref ?ref .}
			}
			?ref biopax3:db '""" + database_name + """'^^XMLSchema:string .
			?ref biopax3:id ?idRef .
		}
	"""

	entityToXRefs = defaultdict(set)
	for entity, xref in sparql_wrapper.sparql_query(query):
		entityToXRefs[entity].add(xref)
	return entityToXRefs
