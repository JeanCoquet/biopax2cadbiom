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
This module is used to translate BioPAX to a CADBIOM model.
"""

from __future__ import print_function

# Standard imports
import copy, dill, sympy, os, re
import itertools as it
from collections import defaultdict
import csv

# Custom imports
from biopax2cadbiom import sparql_biopaxQueries as query
from biopax2cadbiom.cadbiom_writer import createCadbiomFile
import biopax2cadbiom.commons as cm

LOGGER = cm.logger()


def addReactionToEntities(dictReaction, dictControl, dictPhysicalEntity):
	"""Fill the attribute 'reactions' of PhysicalEntity objects.

	.. note:: The value corresponds to a set of reactions involving entity.

	.. note:: Supported roles in reactions are:
		- productComponent
		- participantComponent
		- leftComponents
		- rightComponents
		- controller of

	:param dictReaction: Dictionnary of biopax reactions,
		created by the function query.getReactions()
	:param dictControl: Dictionnary of biopax controls,
		created by the function query.getControls()
	:param dictPhysicalEntity: Dictionnary of biopax physicalEntities,
		created by the function query.getPhysicalEntities()
	:type dictReaction: <dict <str>: <Reaction>>
		keys: uris; values reaction objects
	:type dictControl: <dict <str>: <Control>>
		keys: uris; values control objects
	:type dictPhysicalEntity: <dict <str>: <PhysicalEntity>>
		keys: uris; values entity objects
	"""

	# Add reactions where each entity is involved
	for uri, reaction in dictReaction.iteritems():
		if reaction.productComponent != None:
			entity_uri = reaction.productComponent
			dictPhysicalEntity[entity_uri].reactions.add(reaction)

		if reaction.participantComponent != None:
			entity_uri = reaction.participantComponent
			dictPhysicalEntity[entity_uri].reactions.add(reaction)

		for entity_uri in reaction.leftComponents | reaction.rightComponents:
			dictPhysicalEntity[entity_uri].reactions.add(reaction)

	# Add reactions controlled by each entity
	for uri, control in dictControl.iteritems():
		# Here, thanks to filter_control() we have only entities
		# Each controller (control.controller) is an entity (not a pathway)
		# So each entity controls a reaction
		if control.controller != None and control.reaction != None:
			dictPhysicalEntity[control.controller].reactions.add(
				control.reaction
			)


def detectMembersUsedInEntities(dictPhysicalEntity, convertFullGraph=False):
	"""Set the attribute 'membersUsed' of entities in the dict dictPhysicalEntity.

	.. note:: The value is False if the entity does not have members;
		if at least one member is involved in a reaction the value is True.

	:param dictPhysicalEntity: Dictionnary of biopax physicalEntities,
		created by the function query.getPhysicalEntities()
	:param convertFullGraph: (optional) Convert all entities to cadbiom node,
		even the entities that are not used elsewhere.
	:type dictPhysicalEntity: <dict <str>: <PhysicalEntity>>
		keys: uris; values entity objects
	:type convertFullGraph: <bool>
	"""

	for entity in dictPhysicalEntity.itervalues():
		entity.membersUsed = convertFullGraph

		if convertFullGraph:
			continue

		# convertFullGraph is False:
		# Try to detect if members of the current entity
		# are used elsewhere in the model.
		# ie: if members of the complex are used in almost 1 reaction
		for subEntity in entity.members:
			# TODO: IL PEUT Y AVOIR DES ENTITY NON REFERENCEE
			# todo: grave ? on en fait quoi ??
			# EX: http://www.reactome.org/biopax/60/48887#Complex5918
			if (subEntity in dictPhysicalEntity) and \
				len(dictPhysicalEntity[subEntity].reactions) != 0:
				# The complex will be "deconstructed" because
				# it is not elementary.
				entity.membersUsed = True
				break


# TODO: Test this function
def developComplexs(dictPhysicalEntity):
	"""Set the attribute 'listOfFlatComponents' of entities in the dict dictPhysicalEntity.

	.. note:: The value corresponds to a list of component sets.

	:param dictPhysicalEntity: Dictionnary of biopax physicalEntities,
		created by the function query.getPhysicalEntities()
	:type dictPhysicalEntity: <dict <str>: <PhysicalEntity>>
		keys: uris; values entity objects
	"""

	# /!\ dictPhysicalEntity will be modified in place
	[developComplexEntity(entity_uri, dictPhysicalEntity)
		for entity_uri, entity in dictPhysicalEntity.iteritems()
			if (entity.entityType == "Complex") and \
				(len(entity.listOfFlatComponents) == 0)]


def developComplexEntity(complexEntity, dictPhysicalEntity):
	"""This procedure fills the value of dictPhysicalEntity[entity]['listOfFlatComponents'].

	:param complexEntity: the biopax id of a complex entity
	:param dictPhysicalEntity: the dictionnary of biopax physicalEntities created by the function query.getPhysicalEntities()
	:type complexEntity: string
	:type dictPhysicalEntity: dict
	"""
	listOfComponentsDevelopped = list()
	for component in dictPhysicalEntity[complexEntity].components:
		if component in dictPhysicalEntity and dictPhysicalEntity[component].entityType != set() :
			typeName = dictPhysicalEntity[component].entityType
			if typeName == "Complex":
				if len(dictPhysicalEntity[component].listOfFlatComponents) == 0:
					developComplexEntity(component, dictPhysicalEntity)
				listOfComponentsDevelopped.append(dictPhysicalEntity[component].listOfFlatComponents)
			elif len(dictPhysicalEntity[component].members) != 0 and dictPhysicalEntity[component].membersUsed:
				listOfComponentsDevelopped.append(list(dictPhysicalEntity[component].members))
			else:
				listOfComponentsDevelopped.append([component])

	if len(listOfComponentsDevelopped) != 0:
		dictPhysicalEntity[complexEntity].listOfFlatComponents = []
		for elements in it.product(*listOfComponentsDevelopped):
			l = []
			for e in elements:
				if isinstance(e, tuple): l += e
				else: l.append(e)
			dictPhysicalEntity[complexEntity].listOfFlatComponents.append(tuple(l))


def addControllersToReactions(dictReaction, dictControl):
	"""Fill the attribute 'controllers' of Reaction objects.

	.. note:: The value corresponds to a set of controller entities involved
		in reaction.

	:param dictReaction: Dictionnary of biopax reactions created,
		by the function query.getReactions()
	:param dictControl: Dictionnary of biopax controls created,
		by the function query.getControls()
	:type dictReaction: <dict <str>: <Reaction>>
		keys: uris; values reaction objects
	:type dictControl: <dict <str>: <Control>>
		keys: uris; values control objects
	"""

	# Get control objects
	for uri, control in dictControl.iteritems():
		# uri reaction
		reaction = control.reaction

		# uris (reaction and controller)
		# We don't want control with empty controller !
		# TODO: filtrer /vérifier ça à la création de l'objet non ?
		# TODO: pourquoi cette vérif ?
		if reaction != None and control.controller != None:

			# TODO: on fait quoi si cette uri n'est pas dans les réactions ??
			if reaction in dictReaction:
				# update reaction object with control object
				dictReaction[reaction].controllers.add(control)


def numerotateLocations(dictLocation, full_compartment_name=False):
	"""Create an cadbiom ID for each location.

	..warning:: It adds the key 'cadbiomId' to the dict dictLocation[location].

	:param dictLocation: Dictionnary of biopax locations created by
		query.getLocations().
		keys: CellularLocationVocabulary uri; values: Location object
	:param full_compartment_name: (optional) If True compartments will be
		encoded on the base of their real names instead of numeric values.
	:type dictLocation: <dict>
	:type full_compartment_name: <bool>
	:returns: idLocationToLocation
		keys: numeric value; values: Location object
	:rtype: <dict>
	"""

	def clean_name(name):
		"""Clean name for correct cadbiom parsing."""

		return re.sub('([^a-zA-Z0-9_])', '_', name)


	idLocationToLocation = {}

	for currentId, location_uri in enumerate(sorted(dictLocation.keys())):

		location = dictLocation[location_uri]

		# Encode compartments names
		if full_compartment_name:
			currentId = clean_name(location.name)

		idLocationToLocation[str(currentId)] = location
		# Update dictLocation with encoded id
		location.cadbiomId = str(currentId)

	LOGGER.debug("Encoded locations: " + str(idLocationToLocation))

	return idLocationToLocation


def getPathwayToPhysicalEntities(dictReaction, dictControl, dictPhysicalEntity):
	"""This function creates the dictionnary pathwayToPhysicalEntities.

	:param dictReaction: Dictionnary of biopax reactions,
		created by the function query.getReactions()
	:param dictControl: Dictionnary of biopax controls,
		created by the function query.getControls()
	:param dictPhysicalEntity: Dictionnary of biopax physicalEntities,
		created by the function query.getPhysicalEntities()
	:type dictReaction: <dict <str>: <Reaction>>
		keys: uris; values reaction objects
	:type dictControl: <dict <str>: <Control>>
		keys: uris; values control objects
	:type dictPhysicalEntity: <dict <str>: <PhysicalEntity>>
		keys: uris; values entity objects
	:returns: pathwayToPhysicalEntities
		keys: pathway uris; values set of entities involved in the pathway.
	:rtype: <dict <str>: <set>>
	"""
	pathwayToPhysicalEntities = defaultdict(set)
	allPhysicalEntities = set(dictPhysicalEntity.keys())

	for reaction in dictReaction:
		physicalEntities = set()
		physicalEntities.add(dictReaction[reaction].productComponent)
		physicalEntities.add(dictReaction[reaction].participantComponent)
		physicalEntities |= dictReaction[reaction].leftComponents
		physicalEntities |= dictReaction[reaction].rightComponents
		physicalEntities &= allPhysicalEntities

		for pathway in dictReaction[reaction].pathways:
			pathwayToPhysicalEntities[pathway] |= physicalEntities

	for control in dictControl:
		if dictControl[control].controller in allPhysicalEntities:
			reaction = dictControl[control].reaction
			for pathway in dictReaction[reaction].pathways:
				pathwayToPhysicalEntities[pathway].add(dictControl[control].controller)

	return pathwayToPhysicalEntities


def addCadbiomNameToEntities(dictPhysicalEntity, dictLocation):
	"""Add 'cadbiomName' and 'listOfCadbiomNames' attributes to entities
	in dictPhysicalEntity.

	.. note:: The attribute 'cadbiomName' corresponds to an unique
		cadbiom ID for the entity.

	.. note:: The attribute 'listOfCadbiomNames' corresponds to a list
		of unique cadbiom IDs.
		Each member of the list is a unique cadbiom ID of each
		subcomponent in the attribute 'listOfFlatComponents'.

	:param dictPhysicalEntity: Dictionnary of biopax physicalEntities,
		created by the function query.getPhysicalEntities()
	:param dictLocation: Dictionnary of biopax locations created by
		query.getLocations().
		keys: CellularLocationVocabulary uri; values: Location object
	:type dictPhysicalEntity: <dict <str>: <PhysicalEntity>>
		keys: uris; values entity objects
	:type dictLocation: <dict>
	"""

	# Get all names and entities for them
	entities_cadbiom_names = defaultdict(set)
	for entity in dictPhysicalEntity.values():
		cadbiomName = getCadbiomName(entity, dictLocation)
		entities_cadbiom_names[cadbiomName].add(entity)

	# Set of unique cadbiom names (not used more than 1 time)
	unique_cadbiom_names = \
		{cadbiom_name for cadbiom_name, entities
			in entities_cadbiom_names.iteritems() if len(entities) == 1}

	# Key: name, value: entities using this name
	for cadbiom_name, entities in entities_cadbiom_names.iteritems():
		# test findunique directement ici ?
		if len(entities) == 1:
			# This name is used only 1 time
			next(iter(entities)).cadbiomName = cadbiom_name
		else:
			# This name is used by many entities.
			# We decide to replace it by a unique name for each entity
			# and convert it according to cadbiom rules
			# Key: uri, value: unique name
			unique_cadbiom_synonyms = findUniqueCadbiomSynonym(
				cadbiom_name,
				{entity.uri for entity in entities},
				unique_cadbiom_names,
				dictPhysicalEntity,
				dictLocation,
			)

			# Set synonyms found to each entity
			for entity in entities:
				entity.cadbiomName = unique_cadbiom_synonyms[entity.uri]

	# Attribution of names for complex/classes with subentities
	for uri, entity in dictPhysicalEntity.iteritems():
		if len(entity.listOfFlatComponents) == 1:
			# 1 sub component:
			# listOfCadbiomNames will contain the parent's name
			entity.listOfCadbiomNames.append(entity.cadbiomName)
		else:
			# Many sub components
			# listOfFlatComponents will contain a list of subcomponent's names
			for flatComponents in entity.listOfFlatComponents:
				s = entity.cadbiomName + "_".join(
					[dictPhysicalEntity[subEntity].cadbiomName
						for subEntity in flatComponents]
				)
				entity.listOfCadbiomNames.append(s)


def findUniqueCadbiomSynonym(cadbiom_name, entity_uris, unique_cadbiom_names, dictPhysicalEntity, dictLocation):
	"""create the dictionnary entityToUniqueSynonym from a
	set of entity uris having the same cadbiom name.

	.. todo:: COMMENTAIRES !

	:param cadbiom_name: the redundant cadbiom name
	:param entity_uris: a set set of entity_uris having the same name
	:param unique_cadbiom_names: Set of unique cadbiom names already used
	:param dictPhysicalEntity: Dictionnary of biopax physicalEntities,
		created by the function query.getPhysicalEntities()
	:param dictLocation: Dictionnary of biopax locations created by
		query.getLocations().
		keys: CellularLocationVocabulary uri; values: Location object
	:type cadbiom_name: str
	:type entity_uris: set
	:type unique_cadbiom_names: set
	:type dictPhysicalEntity: <dict <str>: <PhysicalEntity>>
		keys: uris; values entity objects
	:type dictLocation: <dict>
	:returns: entityToUniqueSynonym
	:rtype: dict
	"""

	entityToUniqueSynonym = {}

	while len(entity_uris) != len(entityToUniqueSynonym):
		entityToUniqueSynonyms = {}
		for uri in entity_uris:
			if uri not in entityToUniqueSynonym:
				entityToUniqueSynonyms[uri] = {
					getCadbiomName(dictPhysicalEntity[uri], dictLocation, synonym=synonymEntity)
					for synonymEntity in dictPhysicalEntity[uri].synonyms
				}

		for uri1, uri2 in it.combinations(entityToUniqueSynonyms.keys(), 2):
			synonyms1 = copy.copy(entityToUniqueSynonyms[uri1])
			synonyms2 = copy.copy(entityToUniqueSynonyms[uri2])
			entityToUniqueSynonyms[uri1] -= synonyms2
			entityToUniqueSynonyms[uri2] -= synonyms1

		# Remove cadbiom names already used
		for uri in entityToUniqueSynonyms:
			entityToUniqueSynonyms[uri] -= unique_cadbiom_names

		nbEntitiesSelected = 0
		for entity_uri, cadbiom_synonyms in entityToUniqueSynonyms.iteritems():
			if len(cadbiom_synonyms) > 0:
				cadbiomName = next(iter(cadbiom_synonyms)) # take first element
				entityToUniqueSynonym[entity_uri] = cadbiomName
				unique_cadbiom_names.add(cadbiomName)
				nbEntitiesSelected += 1

		if nbEntitiesSelected == 0:
			for entity_version, entity_uri in enumerate(entityToUniqueSynonyms.keys(), 1):
				entityToUniqueSynonym[entity_uri] = \
					"{}_v{}".format(
						cadbiom_name,
						entity_version,
					)

	return entityToUniqueSynonym


def getCadbiomName(entity, dictLocation, synonym=None):
	"""Get entity name formatted for Cadbiom.

	:param arg1: PhysicalEntity for which the name will be encoded.
	:param arg2: Dictionnary of biopax locations created by
		query.getLocations().
		keys: CellularLocationVocabulary uri; values: Location object
	:param arg3: (Optional) Synonym that will be used instead of the name
		of the given entity.
	:type arg1: <PhysicalEntity>
	:type arg2: <dict>
	:type arg3: <str>
	:return: Encoded name with location if it exists.
	:rtype: <str>
	"""

	def clean_name(name):
		"""Clean name for correct cadbiom parsing."""

		return re.sub('([^a-zA-Z0-9_])', '_', name)


	if synonym:
		name = synonym
	else:
		# Check if name is present, otherwise take the uri
		name = entity.name if entity.name else entity.uri.rsplit("#", 1)[1]

	# Add location id to the name if it exists
	location_uri = entity.location
	return \
		clean_name(name) + "_" + dictLocation[location_uri].cadbiomId \
			if location_uri else clean_name(name)


def getSetOfCadbiomPossibilities(entity, dictPhysicalEntity):
	"""
	set de composants possibles pour 1 complexe

	:param entity: A Physical entity object that is a controller.
	:param dictPhysicalEntity: Dictionnary of biopax physicalEntities,
		created by the function query.getPhysicalEntities()
	:type entity: <PhysicalEntity>
	:type dictPhysicalEntity: <dict <str>: <PhysicalEntity>>
		keys: uris; values entity objects
	:return:
	:rtype: <set>
	"""
	cadbiomPossibilities = set()

	# TODO: pourquoi ces conditions ??!
	if len(entity.listOfFlatComponents) != 0:
		cadbiomPossibilities = set(entity.listOfCadbiomNames)
	elif len(entity.members) != 0 and entity.membersUsed:
		# It's a class with members that are used elsewhere: Destruct it
		for subEntity in entity.members:
			cadbiomPossibilities |= \
				getSetOfCadbiomPossibilities(
					dictPhysicalEntity[subEntity],
					dictPhysicalEntity
				)
	else:
		cadbiomPossibilities.add(entity.cadbiomName)

	return cadbiomPossibilities


def get_control_group_condition(controls, dictPhysicalEntity):
	"""Get condition a group of controllers, linked by the same evidences.

	:param controls: Set of Control objects.
	:param dictPhysicalEntity: Dictionnary of biopax physicalEntities,
		created by the function query.getPhysicalEntities()
	:type dictPhysicalEntity: <dict <str>: <PhysicalEntity>>
		keys: uris; values entity objects
	:return: Sympy condition.
	:rtype: <sympy.core.symbol.Symbol>
	"""

	sub_sub_cond = None
	# set of Control objects linked by same evidences => Logical AND
	for control in controls:
		possibilities_it = iter(
			getSetOfCadbiomPossibilities(
				dictPhysicalEntity[control.controller],
				dictPhysicalEntity
			)
		)

		if control.controlType == "ACTIVATION" :
			# Init the condition with the first possibility
			sub_cond = sympy.Or(sympy.Symbol(next(possibilities_it)))
			for possibilitity in possibilities_it:
				sub_cond = sympy.Or(sub_cond,
									sympy.Symbol(possibilitity))

		elif control.controlType == "INHIBITION":
			# Init the condition with the first possibility
			sub_cond = sympy.Not(sympy.Symbol(next(possibilities_it)))
			for possibilitity in possibilities_it:
				sub_cond = sympy.Or(sub_cond,
									sympy.Not(sympy.Symbol(possibilitity)))
		else:
			raise AssertionError("You should never have been there ! "
					 "Your Controller type is not supported...")

		# Init the condition with the first controller
		if sub_sub_cond == None:
			sub_sub_cond = sub_cond
		else:
			sub_sub_cond = sympy.And(sub_sub_cond, sub_cond)

	return sub_sub_cond


def addCadbiomSympyCondToReactions(dictReaction, dictPhysicalEntity):
	"""Forge condition for each reaction.

	:param dictReaction: Dictionnary of biopax reactions,
		created by the function query.getReactions()
	:param dictPhysicalEntity: Dictionnary of biopax physicalEntities,
		created by the function query.getPhysicalEntities()
	:type dictReaction: <dict <str>: <Reaction>>
		keys: uris; values reaction objects
	:type dictPhysicalEntity: <dict <str>: <PhysicalEntity>>
		keys: uris; values entity objects
	"""

	# Begin event's numeration from 1
	for event_number, (_, reaction) in enumerate(dictReaction.iteritems(), 1):

		# Get groups of controllers that regulate the same reaction
		# => Conditions IN a group are linked to each other with a logical AND
		# => Groups are linked to each other with a logical OR
		# (because there is no evidence which proves that they regulate at the
		# same time the same reaction).
		# key: <set of uris>; value: <Control>
		groups_of_controllers = defaultdict(set)
		for control in reaction.controllers:
			groups_of_controllers[frozenset(control.evidences)].add(control)

		# We don't care of the dict key (set of evidence) for the moment.
		# TODO: souvent, des sets sont VIDES. => pas d'évidence.
		# Comment statuer sur le fait que ces controlleurs agissent
		# en meme temps ou non sur la reaction ?
		cadbiomSympyCond = None
		# Set of Groups of Controllers. Groups are linked with a logical OR
		for controls in groups_of_controllers.values():

			# Get condition for the given group of controllers,
			# linked by the same evidences => Logical AND
			sub_sub_cond = get_control_group_condition(
				controls,
				dictPhysicalEntity
			)

			# Init the condition with the first controller
			if cadbiomSympyCond == None:
				cadbiomSympyCond = sub_sub_cond
			else:
				cadbiomSympyCond = sympy.Or(cadbiomSympyCond, sub_sub_cond)


		# No controller ?
		if cadbiomSympyCond == None:
			reaction.cadbiomSympyCond = sympy.sympify(True)
		else:
			reaction.cadbiomSympyCond = cadbiomSympyCond

		reaction.event = "_h_" + str(event_number)


def getListOfPossibilitiesAndCadbiomNames(entity, dictPhysicalEntity):
	"""
	:return: list of tuples (uris, name)
	:rtype: <list>
	"""

	listOfEquivalentsAndCadbiomName = []

	if len(entity.listOfFlatComponents) != 0:
		for i in range(len(entity.listOfFlatComponents)):
			flatComponents = entity.listOfFlatComponents[i]
			cadbiomName = entity.listOfCadbiomNames[i]
			listOfEquivalentsAndCadbiomName.append((flatComponents,cadbiomName))

	elif len(entity.members) != 0 and entity.membersUsed:
		for subEntity in entity.members:
			listOfEquivalentsAndCadbiomName += \
				getListOfPossibilitiesAndCadbiomNames(dictPhysicalEntity[subEntity], dictPhysicalEntity)
	else:
		listOfEquivalentsAndCadbiomName.append((tuple([entity.uri]),entity.cadbiomName))

	return listOfEquivalentsAndCadbiomName


def refInCommon(entities1, entities2, dictPhysicalEntity):
	"""Check common references between 2 sets of entities.

	.. note:: This function is used to make a transition between 2 set of
		entities. => Is there any transition between these 2 sets ?


	:param entities1: List of uris of entities.
	:param entities2: List of uris of entities.
	:param dictPhysicalEntity: Dictionnary of biopax physicalEntities,
		created by the function query.getPhysicalEntities()
	:type entities1: <list>
	:type entities2: <list>
	:type dictPhysicalEntity: <dict <str>: <PhysicalEntity>>
		keys: uris; values entity objects
	:return: False if a set of entities have no entityRefs or if
		entityRefs in 1 are not in 2 and if entityRefs in 2 are not in 1.
		True otherwhise or if entities1 is a subset of entities2,
		or if entities2 is a subset of entities1.
	:rtype: <bool>
	"""

	# Check if entities in 1 are in 2, or entities in 2 are in 1
	if set(entities1) <= set(entities2) or set(entities1) >= set(entities2):
		return True

	# Get all entityRefs from entities1 (if they are present in these entities)
	g = (dictPhysicalEntity[entity_uri].entityRef for entity_uri in entities1)
	entityRefs1 = {entity_ref for entity_ref in g if entity_ref != None}

	# Get all entityRefs from entities2 (if they are present in these entities)
	g = (dictPhysicalEntity[entity_uri].entityRef for entity_uri in entities2)
	entityRefs2 = {entity_ref for entity_ref in g if entity_ref != None}

	if len(entityRefs1) == 0 or len(entityRefs2) == 0:
		return False
	# Check if entities in 1 are in 2, or entities in 2 are in 1
	return (entityRefs1 <= entityRefs2) or (entityRefs1 >= entityRefs2)


def getProductCadbioms(entities, entityToListOfEquivalentsAndCadbiomName):
	"""Get all cartesian product of all possible names of entities.

	:return:
		.. example::
		Input:
		set([u'http://pathwaycommons.org/pc2/#Complex_aa82041945ad0f6a68f33a25a9720863', u'http://pathwaycommons.org/pc2/#Complex_3fe118eaca425fc3b269b691cd9239df', u'http://pathwaycommons.org/pc2/#Protein_597e0393013973540c8ec5d34766c8b0'])
		Output:
		[(u'AP_2_adaptor_complex', 'IL8_CXCR2_v2_integral_to_membrane', u'beta_Arrestin1'), (u'AP_2_adaptor_complex', 'IL8_CXCR2_v2_integral_to_membrane', 'beta_Arrestin2_v1')]

	"""

	# Get a list of cadbiom names, for each entity
	cadbiom_names_per_entity = list()
	[cadbiom_names_per_entity.append(
		# Get all possible names for this entity
		[name for _, name in entityToListOfEquivalentsAndCadbiomName[uri]]
	) for uri in entities]

	return it.product(*cadbiom_names_per_entity)


def getProductCadbiomsMatched(entities, entityToListOfEquivalentsAndCadbiomName,
							  entityToEntitiesMatched):

	# Get a list of cadbiom names, for each entity if entityToEntitiesMatched ????
	cadbiom_names_per_entity = list()
	[cadbiom_names_per_entity.append(
		# Get all possible names for this entity
		[name for _, name in entityToListOfEquivalentsAndCadbiomName[uri]]
	) for uri in entities if entityToEntitiesMatched[uri] != set()]

	return it.product(*cadbiom_names_per_entity)


def getEntityNameUnmatched(entities, entityToEntitiesMatched,
						   dictPhysicalEntity):

	return {dictPhysicalEntity[entity].cadbiomName for entity in entities
		if entityToEntitiesMatched[entity] == set()}


def updateTransitions(reaction, dictPhysicalEntity, dictTransition):
	"""

	"""


	def update_subtransitions(left_entity, right_entity, event, cond):
		""".. todo: Move this function and reuse it elsewhere.
		"""

		subDictTransition[(left_entity, right_entity)].append(
			{
				'event': event,
				'reaction': reaction.uri,
				'sympyCond': cond,
			}
		)


	leftEntities = reaction.leftComponents
	rightEntities = reaction.rightComponents

	entityToListOfEquivalentsAndCadbiomName = {}
	for entity in leftEntities|rightEntities:
		entityToListOfEquivalentsAndCadbiomName[entity] = \
			getListOfPossibilitiesAndCadbiomNames(dictPhysicalEntity[entity], dictPhysicalEntity)

	cadbiomToCadbiomsMatched = defaultdict(set)
	entityToEntitiesMatched = defaultdict(set)
	match = False
	for entity1, entity2 in it.combinations(entityToListOfEquivalentsAndCadbiomName.keys(),2):
		for equis1,cadbiom1 in entityToListOfEquivalentsAndCadbiomName[entity1]:
			for equis2,cadbiom2 in entityToListOfEquivalentsAndCadbiomName[entity2]:
				if refInCommon(equis1, equis2, dictPhysicalEntity):
					cadbiomToCadbiomsMatched[cadbiom1].add(cadbiom2)
					cadbiomToCadbiomsMatched[cadbiom2].add(cadbiom1)
					entityToEntitiesMatched[entity1].add(entity2)
					entityToEntitiesMatched[entity2].add(entity1)
					match = True

	presenceOfMembers = False
	for entity in leftEntities|rightEntities:
		if len(dictPhysicalEntity[entity].listOfFlatComponents) > 1 or (len(dictPhysicalEntity[entity].members) > 1 and dictPhysicalEntity[entity].membersUsed):
			presenceOfMembers = True
			break

	subDictTransition = defaultdict(list)
	subH = 1

	if not match or not presenceOfMembers:
		for productCadbiomsL in getProductCadbioms(leftEntities, entityToListOfEquivalentsAndCadbiomName):
			for productCadbiomsR in getProductCadbioms(rightEntities, entityToListOfEquivalentsAndCadbiomName):
				for cadbiomL, cadbiomR in it.product(productCadbiomsL,productCadbiomsR):
					transitionSympyCond = reaction.cadbiomSympyCond
					for otherCadbiomL in set(productCadbiomsL)-set([cadbiomL]):
						sympySymbol = sympy.Symbol(otherCadbiomL)
						transitionSympyCond = sympy.And(transitionSympyCond, sympySymbol)

					update_subtransitions(
						cadbiomL, cadbiomR,
						reaction.event + "_" + str(subH),
						transitionSympyCond,
					)

				subH += 1

	else:
		for productCadbiomsL in getProductCadbiomsMatched(leftEntities, entityToListOfEquivalentsAndCadbiomName, entityToEntitiesMatched):
			for productCadbiomsR in getProductCadbiomsMatched(rightEntities, entityToListOfEquivalentsAndCadbiomName, entityToEntitiesMatched):

				isValidTransition = True
				for cadbiomL in productCadbiomsL:
					if len(cadbiomToCadbiomsMatched[cadbiomL]&set(productCadbiomsR)) == 0:
						isValidTransition = False
						break
				for cadbiomR in productCadbiomsR:
					if len(cadbiomToCadbiomsMatched[cadbiomR]&set(productCadbiomsL)) == 0:
						isValidTransition = False
						break
				if isValidTransition:
					cadbiomsR = set(productCadbiomsR)|getEntityNameUnmatched(rightEntities, entityToEntitiesMatched, dictPhysicalEntity)

					for cadbiomL, cadbiomR in it.product(productCadbiomsL,cadbiomsR):
						transitionSympyCond = reaction.cadbiomSympyCond
						for otherCadbiomL in set(productCadbiomsL)-set([cadbiomL]):
							sympySymbol = sympy.Symbol(otherCadbiomL)
							transitionSympyCond = sympy.And(transitionSympyCond, sympySymbol)

						update_subtransitions(
							cadbiomL, cadbiomR,
							reaction.event + "_" + str(subH),
							transitionSympyCond,
						)
					subH += 1

		for entityR in rightEntities:
			if entityToEntitiesMatched[entityR] == set():
				nameEntityR = dictPhysicalEntity[entityR].cadbiomName
				for subEquis,subCadbiom in entityToListOfEquivalentsAndCadbiomName[entityR]:
					transitionSympyCond = reaction.cadbiomSympyCond

					update_subtransitions(
						nameEntityR, subCadbiom,
						reaction.event + "_" + str(subH),
						transitionSympyCond,
					)
					subH += 1

		currentKeys = list(subDictTransition.keys())
		for entityL in leftEntities:
			if entityToEntitiesMatched[entityL] == set():
				for equisL,cadbiomL in entityToListOfEquivalentsAndCadbiomName[entityL]:
					for left,right in currentKeys:
						for transition in subDictTransition[(left,right)]:
							transitionSympyCond = transition['sympyCond']
							sympySymbol = sympy.Symbol(left)
							transitionSympyCond = sympy.And(transitionSympyCond, sympySymbol)

							update_subtransitions(
								cadbiomL, right,
								transition['event'],
								transitionSympyCond,
							)

	for left_right, transitions in subDictTransition.iteritems():
		for transition in transitions:
			if subH > 2:
				event = transition['event']
			else:
				event = reaction.event

			dictTransition[left_right].append({
				'event': event,
				'reaction': reaction.uri,
				'sympyCond': transition['sympyCond']
			})


def getTransitions(dictReaction, dictPhysicalEntity):
	"""Return transitions with (ori/ext nodes) and their respective events.

	.. warning:: dictPhysicalEntity is modified in place.
		We add "virtual nodes" for genes that are not in BioPAX format.

	.. todo:: handle TRASH nodes => will crash cadbiom writer because
		they are not entities...

	:param dictReaction: Dictionnary of biopax reactions,
		created by the function query.getReactions()
	:param dictPhysicalEntity: Dictionnary of biopax physicalEntities,
		created by the function query.getPhysicalEntities()
	:type dictReaction: <dict <str>: <Reaction>>
		keys: uris; values reaction objects
	:type dictPhysicalEntity: <dict <str>: <PhysicalEntity>>
		keys: uris; values entity objects
	:return: Dictionnary of transitions and their respective set of events.
		.. example::
			subDictTransition[(cadbiomL,right)].append({
				'event': transition['event'],
				'reaction': reaction,
				'sympyCond': transitionSympyCond
			}
	:rtype: <dict <tuple <str>, <str>>: <list <dict>>>
	"""

	def update_transitions(left_entity, right_entity, reaction):
		""".. todo: Move this function and reuse it elsewhere.
		"""

		dictTransition[(left_entity, right_entity)].append(
			{
				'event': reaction.event,
				'reaction': reaction.uri,
				'sympyCond': reaction.cadbiomSympyCond
			}
		)


	dictTransition = defaultdict(list)

	reaction_types = ("BiochemicalReaction", "ComplexAssembly", "Transport",
			"TransportWithBiochemicalReaction")
	regulator_types = ("Catalysis", "Control", "TemplateReactionRegulation")

	for reaction_uri, reaction in dictReaction.iteritems():

		typeName = reaction.reactiontype

		if typeName in reaction_types:
			# ATTENTION: que faire si 'leftComponents'
			# ou bien 'rightComponents' sont vides ?
			# /!\ This modifies dictTransition in place
			updateTransitions(
				reaction, dictPhysicalEntity, dictTransition
			)

		elif typeName == "Degradation":
			# Reaction of degradation = Suppression of entities
			# Normally there is just one component
			assert len(reaction.rightComponents) == 0, \
				"The degradation reaction {}, contains an output entity" \
				" (right) ! Please check this !".format(reaction_uri)

			for entityL in reaction.leftComponents:
				cadbiomL = dictPhysicalEntity[entityL].cadbiomName

				# /!\ This modifies dictTransition in place
				update_transitions(
					cadbiomL, "#TRASH", reaction
				)

		elif typeName == "TemplateReaction":
			# Reaction of transcription
			# In Cadbiom language: Gene => product of gene
			entityR = reaction.productComponent
			# Sometimes, there is no entityR
			# ex: http://pathwaycommons.org/pc2/#TemplateReaction_3903f25156da4c9000a93bbc85b18572).
			# It is a bug in BioPax.
			if entityR is None:
				LOGGER.error("BioPAX bug; Transcription reaction without" + \
							 " product: " + reaction_uri)
			else:
				# Update dictPhysicalEntity with entities corresponding to genes
				# PS: These entities are not in BioPAX formalisation
				cadbiomR = dictPhysicalEntity[entityR]
				cadbiomL = copy.deepcopy(cadbiomR)
				cadbiomL.cadbiomName += '_gene'
				cadbiomL.uri = reaction_uri
				# /!\ This modifies dictPhysicalEntity in place
				dictPhysicalEntity[reaction_uri] = cadbiomL

				# /!\ This modifies dictTransition in place
				update_transitions(
					cadbiomL.cadbiomName, cadbiomR.cadbiomName, reaction
				)

		elif typeName in regulator_types:
			continue

		else:
			LOGGER.error("UNEXCEPTED REACTION: " + reaction_uri)
			raise AssertionError("UNEXCEPTED REACTION: " + reaction_uri)

	return dictTransition


def filter_control(controls, pathways_names, cofactors=set()):
	"""Remove pathways from controls and keep others (entities + ?).

	We want ONLY entities and by default there are pathways + entities.

	:param arg1: Contollers.
	:param arg2: Dict of pathways URIs and names.
		keys: URIs; values: names (or uri if no name)
	:type arg1: <dict>
	:type arg2: <dict>
	:return: Filtered controllers dict.
	:rtype: <dict>
	"""

	blacklisted_controllers = set(pathways_names.keys()) | cofactors

	return {control: controls[control] for control in controls
			if controls[control].controller not in blacklisted_controllers}

def filter_entity(dictPhysicalEntity, blacklisted_entities):
	"""Remove blacklisted entities from entities.

	:param dictPhysicalEntity: Dictionnary of biopax physicalEntities,
		created by the function query.getPhysicalEntities()
	:param blacklisted_entities: set of entity uris blacklisted
	:type dictPhysicalEntity: <dict <str>: <PhysicalEntity>>
		keys: uris; values entity objects
	:type blacklisted_entities: <set>
	:return: Dictionnary of biopax physicalEntities without entities blacklisted
	:rtype: <dict <str>: <PhysicalEntity>>
	"""
	dictPhysicalEntityFiltered = {entity_uri: dictPhysicalEntity[entity_uri] for entity_uri in dictPhysicalEntity
			if entity_uri not in blacklisted_entities}

	# Remove blacklisted entities from members and components
	for entity_uri, entity in dictPhysicalEntityFiltered.iteritems():
		entity.components.difference_update(blacklisted_entities)
		entity.members.difference_update(blacklisted_entities)

	return dictPhysicalEntityFiltered


def removeEntitiesBlacklistedFromReactions(dictReaction, blacklisted_entities):
	"""Remove blacklisted entities from reactions.

	:param dictReaction: Dictionnary of biopax reactions,
		created by the function query.getReactions()
	:param blacklisted_entities: set of entity uris blacklisted
	:type dictReaction: <dict <str>: <Reaction>>
		keys: uris; values reaction objects
	:type blacklisted_entities: <set>
	"""
	for reaction_uri, reaction in dictReaction.iteritems():
		reaction.leftComponents.difference_update(blacklisted_entities)
		reaction.rightComponents.difference_update(blacklisted_entities)

		if reaction.productComponent in blacklisted_entities:
			reaction.productComponent = None
		if reaction.participantComponent in blacklisted_entities:
			reaction.participantComponent = None


def load_blacklisted_entities(blacklist):
	"""Get all uris of blacklisted elements in the given file.

	.. note:: The csv can be written with ',;' delimiters.
		In the first column we expect the uri,
		In the second users can put the corresponding cadbiom name (not used).

	:param: Blacklist filename.
	:type: <str>
	:return: Set of uris.
	:rtype: <set>
	"""

	with open(blacklist, 'r') as fd:

		# Try to detect csv format
		dialect = csv.Sniffer().sniff(fd.read(1024), delimiters=',;')
		fd.seek(0)

		reader = csv.reader(fd, dialect)

		# Take uri in first position only, right now...
		return {line[0] for line in reader}


def createControlFromEntityOnBothSides(dictReaction, dictControl):
	"""Remove from reaction the entity on both sides and create a control instead.

	:param dictReaction: Dictionnary of biopax reactions,
		created by the function query.getReactions()
	:param dictControl: Dictionnary of biopax controls,
		created by the function query.getControls()
	:type dictReaction: <dict <str>: <Reaction>>
		keys: uris; values reaction objects
	:type dictControl: <dict <str>: <Control>>
		keys: uris; values control objects
	"""

	for reaction_uri, reaction in dictReaction.iteritems():
		# extract entity_uri at the same time in reaction.leftComponents and in reaction.rightComponents
		for entityOnBothSides_uri in reaction.leftComponents&reaction.rightComponents:
			# remove from reaction the entity on both sides
			reaction.leftComponents.remove(entityOnBothSides_uri)
			reaction.rightComponents.remove(entityOnBothSides_uri)

			# create a entity control of the reaction 
			# that entity is not in original BioPAX data
			# /!\ the control uri is formatted by reactionUri+entityUri
			control = Control(reaction.uri+"+"+entityOnBothSides_uri, "entityOnBothSides", "ACTIVATION", reaction.uri, entityOnBothSides_uri)
			dictControl[control.uri] = control


def main(params):
	"""Entry point

	Here we detect the presence of the pickle backup and of its settings.
	If there is no backup or if the user doesn't want to use this functionality,
	normal queries are made against the triplestore.

	We construct a Cadbiom model with all the data retrieved.

	"""

	backup_file_status = os.path.isfile(params['pickleDir'])

	# Set triplestore url
	cm.SPARQL_PATH = params['triplestore']

	# No pickle or not backup file => do queries
	if not params['pickleBackup'] or not backup_file_status:

		# Load entities to be blacklisted from conditions
		blacklisted_entities = set()
		if params['blacklist'] is not None:
			blacklisted_entities = \
				load_blacklisted_entities(params['blacklist'])

		# Query the SPARQL endpoint
		dictPhysicalEntity = \
			filter_entity(
				query.getPhysicalEntities(params['listOfGraphUri']),
				blacklisted_entities
			)

		dictReaction	= query.getReactions(params['listOfGraphUri'])
		dictLocation	= query.getLocations(params['listOfGraphUri'])
		dictPathwayName = query.getPathways(params['listOfGraphUri'])

		# Filter cofactors from controls and remove pathways as controllers
		dictControl = \
			filter_control(
				query.getControls(params['listOfGraphUri']),
				dictPathwayName,
				blacklisted_entities,
			)

	# Pickle but no backup file => save queries
	if params['pickleBackup'] and not backup_file_status:

		LOGGER.debug("Variables saving...")
		dill.dump(
			[
				dictPhysicalEntity, dictReaction, dictLocation, dictControl,
				blacklisted_entities, params
			],
			open(params['pickleDir'], "wb")
		)

	# Pickle and backup file => load queries
	if params['pickleBackup'] and backup_file_status:

		LOGGER.debug("Variables loading...")
		dictPhysicalEntity, dictReaction, dictLocation, dictControl, \
		blacklisted_entities, params_loaded = \
			dill.load(open(params['pickleDir'], "rb"))

		# Check if given parameters are equal to those loaded from backup
		assert params_loaded == params, \
			"The settings are different from those you have previously entered!"


	# Do the magic...
	removeEntitiesBlacklistedFromReactions(dictReaction, blacklisted_entities)

	createControlFromEntityOnBothSides(dictReaction, dictControl)

	addReactionToEntities(dictReaction, dictControl, dictPhysicalEntity)

	detectMembersUsedInEntities(dictPhysicalEntity, params['convertFullGraph'])
	developComplexs(dictPhysicalEntity)
	addControllersToReactions(dictReaction, dictControl)
	numerotateLocations(dictLocation, params['fullCompartmentsNames'])
	addCadbiomNameToEntities(dictPhysicalEntity, dictLocation)
	addCadbiomSympyCondToReactions(dictReaction, dictPhysicalEntity)

	# Compute final transitions
	dictTransition = getTransitions(dictReaction, dictPhysicalEntity)

	# Make the Cadbiom model
	createCadbiomFile(
		dictTransition,
		dictPhysicalEntity,
		str(params['listOfGraphUri']), # model name
		params['cadbiomFile'] # path
	)
