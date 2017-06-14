# -*- coding: utf-8 -*-
"""
This module contains a list of functions to request Reactome
"""

from src import sparql_wrapper
from collections import defaultdict
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
			?pathway biopax3:displayName ?displayName .
		}
	"""

	
	for pathway, name  in sparql_wrapper.sparql_query(query):
		pathwayToName[pathway] = name
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
	for pathway, superPathway in sparql_wrapper.sparql_query(query):
		pathwayToSuperPathways[pathway].add(superPathway)
	return pathwayToSuperPathways


def getReactions(listOfGraphUri):
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
			OPTIONAL { ?reaction biopax3:left ?leftComponent . }
			OPTIONAL { ?reaction biopax3:right ?rightComponent . }
			OPTIONAL { ?reaction biopax3:product ?productComponent . }
			OPTIONAL { ?reaction biopax3:participant ?participantComponent . }
		}
	"""
	# ATTENTION: si on fait 'rdfs:subClassOf* biopax3:Interaction' alors on recupere aussi les 'Control', ce qui est doit etre fait par getControls(listOfGraphUri)

	for reaction, \
		nameReaction, \
		reactionType, \
		pathway, \
		leftComponent, \
		rightComponent, \
		productComponent, \
		participantComponent in sparql_wrapper.sparql_query(query):
		if reaction not in dictReaction:
			dictReaction[reaction] = Reaction(reaction, nameReaction, reactionType, productComponent, participantComponent)
		if pathway != None: dictReaction[reaction].pathways.add(pathway)
		if leftComponent != None: dictReaction[reaction].leftComponents.add(leftComponent)
		if rightComponent != None: dictReaction[reaction].rightComponents.add(rightComponent)

	return dictReaction


def getPhysicalEntities(listOfGraphUri):
	dictPhysicalEntity = {}
	query = """
		SELECT DISTINCT ?entity ?name ?synonym ?location ?type ?component ?member ?entityRef ?dbRef ?idRef
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
			OPTIONAL {
				?entity biopax3:xref ?ref .
				?ref biopax3:db ?dbRef .
				?ref biopax3:id ?idRef .
			}
		}
	"""

	
	for entity, \
		name, \
		synonym, \
		location, \
		entityType, \
		component, \
		member, \
		entityRef, \
		dbRef, \
		idRef in sparql_wrapper.sparql_query(query):
		
		if entity not in dictPhysicalEntity:
			dictPhysicalEntity[entity] = PhysicalEntity(entity, name, location, entityType, entityRef)
		
		if synonym != None: dictPhysicalEntity[entity].synonyms.add(synonym)
		if component != None: dictPhysicalEntity[entity].components.add(component)
		if member != None: dictPhysicalEntity[entity].members.add(member)
		if idRef != None: dictPhysicalEntity[entity].idRefs.add((idRef,dbRef))

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
	
	for location, locationTerm, dbRef, idRef in sparql_wrapper.sparql_query(query):
		if location not in dictLocation:
			dictLocation[location] = Location(location, locationTerm)
		if idRef != None: dictLocation[location].idRefs.add((idRef,dbRef))
	return dictLocation


def getControls(listOfGraphUri):
	dictControl = {}
	query = """
		SELECT DISTINCT ?control ?type ?controlType ?reaction ?controller
	"""
	for graphUri in listOfGraphUri:
		query += "FROM <"+graphUri+">\n"
	query += """
		WHERE
		{
			?control rdf:type ?type.
			?type rdfs:subClassOf* biopax3:Control .
			OPTIONAL { ?control biopax3:controlled ?reaction . }
			OPTIONAL { ?control biopax3:controlType ?controlType . }
			OPTIONAL { ?control biopax3:controller ?controller . }
		}
	"""
	
	for control, \
		classType, \
		controlType, \
		reaction, \
		controller in sparql_wrapper.sparql_query(query):
		if control not in dictControl:
			dictControl[control] = Control(control, classType, controlType, reaction, controller)
	return dictControl
