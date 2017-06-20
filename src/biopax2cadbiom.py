# -*- coding: utf-8 -*-
"""
This module is used to translate biopax to a cadbiom model
"""

from __future__ import print_function

# Standard imports
import itertools, copy, dill, sympy, os, re
from collections import defaultdict
import networkx as nx

# Custom imports
from src import sparql_biopaxQueries as query
from src.cadbiom_writer import createCadbiomFile
import src.commons as cm

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
			entity = reaction.productComponent
			dictPhysicalEntity[entity].reactions.add(reaction)

		if reaction.participantComponent != None:
			entity = reaction.participantComponent
			dictPhysicalEntity[entity].reactions.add(reaction)

		for entity in reaction.leftComponents | reaction.rightComponents:
			dictPhysicalEntity[entity].reactions.add(reaction)

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
	"""This procedure adds the key 'listOfFlatComponents' to the dictionnary dictPhysicalEntity[entity]. The value corresponds to a list of component sets.

	:param dictPhysicalEntity: the dictionnary of biopax physicalEntities created by the function query.getPhysicalEntities()
	:type dictPhysicalEntity: dict
	"""
	for entity in dictPhysicalEntity:
		if dictPhysicalEntity[entity].entityType != set() :
			typeName = dictPhysicalEntity[entity].entityType
			if typeName == "Complex":
				if len(dictPhysicalEntity[entity].listOfFlatComponents) == 0:
					developComplexEntity(entity, dictPhysicalEntity)


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
		for elements in itertools.product(*listOfComponentsDevelopped):
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
		keys: numeric value; values: CellularLocationVocabulary uri
	:rtype: <dict>
	"""

	def clean_name(name):
		"""Clean name for correct cadbiom parsing."""

		return re.sub('([^a-zA-Z0-9_])', '_', name)


	idLocationToLocation = {}

	for currentId, location in enumerate(sorted(dictLocation.keys())):

		# Encode compartments names
		if full_compartment_name:
			currentId = clean_name(dictLocation[location].name)

		idLocationToLocation[str(currentId)] = location
		# Update dictLocation with encoded id
		dictLocation[location].cadbiomId = str(currentId)

	LOGGER.debug("Encoded locations:" + str(idLocationToLocation))

	return idLocationToLocation


def getPathwayToPhysicalEntities(dictReaction, dictControl, dictPhysicalEntity):
	"""This function creates the dictionnary pathwayToPhysicalEntities. The keys are the pathway IDs and the values are the set of entities involved in the pathway.


	:param dictReaction: the dictionnary of biopax reactions created by the function query.getReactions()
	:param dictControl: the dictionnary of biopax controls created by the function query.getControls()
	:param dictPhysicalEntity: the dictionnary of biopax physicalEntities created by the function query.getPhysicalEntities()
	:type dictReaction: dict
	:type dictControl: dict
	:type dictPhysicalEntity: dict
	:returns: pathwayToPhysicalEntities
	:rtype: dict
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


def createGraphOfInteractionsBetweenPathways(pathwayToName, pathwayToSuperPathways, dictTransition, dictReaction, pathGexfFile):
	G = nx.DiGraph()
	for pathway in pathwayToName:
		s = pathwayToName[pathway]
		#if len(pathwayToSuperPathways[pathway]) != 0: s = ""
		G.add_node(pathway, label=s, Type='pathway')

	for pathway in pathwayToSuperPathways:
		for superPathway in pathwayToSuperPathways[pathway]:
			G.add_edge(superPathway, pathway, Type='Inclusion of pathway')

	cadbiomLToPathways = {}
	cadbiomRToPathways = {}
	for cadbiomL,cadbiomR in dictTransition:
		pathways = set()
		for transition in dictTransition[(cadbiomL,cadbiomR)]:
			pathways |= dictReaction[transition.reaction].pathways
		cadbiomLToPathways[cadbiomL] = pathways
		cadbiomRToPathways[cadbiomR] = pathways

	for cadbiomL,cadbiomR in itertools.product(cadbiomLToPathways.keys(),cadbiomRToPathways.keys()):
		if cadbiomL == cadbiomR:
			specificPathwaysR = cadbiomRToPathways[cadbiomR]-cadbiomLToPathways[cadbiomL]
			specificPathwaysL = cadbiomLToPathways[cadbiomL]-cadbiomRToPathways[cadbiomR]
			for pathwayR,pathwayL in itertools.product(specificPathwaysR,specificPathwaysL):
				if not G.has_edge(pathwayR,pathwayL):
					G.add_edge(pathwayR, pathwayL, Type='Sharing of cadbiom nodes')

	nx.write_gexf(G, pathGexfFile)


def addCadbiomNameToEntities(dictPhysicalEntity, dictLocation):
	"""This function creates the dictionnary cadbiomNameToPhysicalEntity, it adds the keys 'cadbiomName' and 'listOfCadbiomNames' to the dictionnary dictPhysicalEntity[entity].
	The value of dictPhysicalEntity[entity]['cadbiomName'] corresponds to an unique cadbiom ID for the entity.
	The value of dictPhysicalEntity[entity]['listOfCadbiomNames'] corresponds to a list if unique cadbiom IDs. Each member of the list is a unique cadbiom ID of each set of dictPhysicalEntity[entity]['listOfFlatComponents'].


	:param dictPhysicalEntity: the dictionnary of biopax physicalEntities created by the function query.getPhysicalEntities()
	:param dictLocation: the dictionnary of biopax reactions created by the function query.getLocations()
	:type dictPhysicalEntity: dict
	:type dictLocation: dict
	:returns: cadbiomNameToPhysicalEntity
	:rtype: dict
	"""
	cadbiomNameToPhysicalEntities = defaultdict(set)

	for entity in dictPhysicalEntity:
		cadbiomName = getCadbiomName(entity, dictPhysicalEntity, dictLocation)
		cadbiomNameToPhysicalEntities[cadbiomName].add(entity)

	cadbiomNameToPhysicalEntity = {}
	for cadbiomName in cadbiomNameToPhysicalEntities:
		if len(cadbiomNameToPhysicalEntities[cadbiomName]) == 1:
			entity = cadbiomNameToPhysicalEntities[cadbiomName].pop()
			cadbiomNameToPhysicalEntity[cadbiomName] = entity
			dictPhysicalEntity[entity].cadbiomName = cadbiomName
		else:
			entities = cadbiomNameToPhysicalEntities[cadbiomName]
			entityToUniqueSynonym = findUniqueSynonym(entities, dictPhysicalEntity)
			for entity in entities:
				cadbiomName = getCadbiomName(entity, dictPhysicalEntity, dictLocation, synonym=entityToUniqueSynonym[entity])
				cadbiomNameToPhysicalEntity[cadbiomName] = entity
				dictPhysicalEntity[entity].cadbiomName = cadbiomName

	for entity in dictPhysicalEntity:
		dictPhysicalEntity[entity].listOfCadbiomNames = []
		if len(dictPhysicalEntity[entity].listOfFlatComponents) == 1:
			dictPhysicalEntity[entity].listOfCadbiomNames.append(dictPhysicalEntity[entity].cadbiomName)
		else:
			for flatComponents in dictPhysicalEntity[entity].listOfFlatComponents:
				s = "_".join([dictPhysicalEntity[subEntity].cadbiomName for subEntity in flatComponents])
				dictPhysicalEntity[entity].listOfCadbiomNames.append(s)
	return cadbiomNameToPhysicalEntity


def findUniqueSynonym(entities, dictPhysicalEntity):
	"""This function creates the dictionnary entityToUniqueSynonym from a set of entities having the same name.

	:param entities: a set set of entities having the same name
	:param dictPhysicalEntity: the dictionnary of biopax reactions created by the function query.getPhysicalEntities()
	:type entities: set
	:type dictPhysicalEntity: dict
	:returns: entityToUniqueSynonym
	:rtype: dict
	"""
	entityToUniqueSynonym = {}

	while len(entities) != len(entityToUniqueSynonym):
		entityToUniqueSynonyms = {}
		for entity in entities:
			if entity not in entityToUniqueSynonym:
				entityToUniqueSynonyms[entity] = copy.copy(dictPhysicalEntity[entity].synonyms)
		for entity1,entity2 in itertools.combinations(entityToUniqueSynonyms.keys(),2):
			entityToUniqueSynonyms[entity1] -= dictPhysicalEntity[entity2].synonyms
			entityToUniqueSynonyms[entity2] -= dictPhysicalEntity[entity1].synonyms

		nbEntitiesSelected = 0
		for entity in entityToUniqueSynonyms:
			if len(entityToUniqueSynonyms[entity]) > 0:
				entityToUniqueSynonym[entity] = dictPhysicalEntity[entity].name+"_("+entityToUniqueSynonyms[entity].pop()+")"
				nbEntitiesSelected += 1

		if nbEntitiesSelected == 0:
			vI = 1
			for entity in entityToUniqueSynonyms:
				entityToUniqueSynonym[entity] = dictPhysicalEntity[entity].name+"_(v"+str(vI)+")"
				vI += 1

	return entityToUniqueSynonym


def getCadbiomName(entity, dictPhysicalEntity, dictLocation, synonym=None):
	"""Get entity name formatted for Cadbiom.

	:param arg1:
	:param arg2:
	:param arg3:
	:param arg4:
	:type arg1:
	:type arg2:
	:type arg3:
	:type arg4:
	:return: Encoded name with location if it exists.
	:rtype: <str>
	"""

	def clean_name(name):
		"""Clean name for correct cadbiom parsing."""

		return re.sub('([^a-zA-Z0-9_])', '_', name)


	if synonym == None:
		if dictPhysicalEntity[entity].name != None:
			name = dictPhysicalEntity[entity].name
		else:
			name = entity.rsplit("#", 1)[1]
	else:
		name = synonym

	# Add location info if exists
	location = dictPhysicalEntity[entity].location
	if location != None and location != set():
		locationId = dictLocation[location].cadbiomId
		return clean_name(name) + "_" + locationId
	else:
		return clean_name(name)


def getSetOfCadbiomPossibilities(entity, dictPhysicalEntity):
	cadbiomPossibilities = set()

	if len(dictPhysicalEntity[entity].listOfFlatComponents) != 0:
		cadbiomPossibilities = set(dictPhysicalEntity[entity].listOfCadbiomNames)
	elif len(dictPhysicalEntity[entity].members) != 0 and dictPhysicalEntity[entity].membersUsed:
		for subEntity in dictPhysicalEntity[entity].members:
			cadbiomPossibilities |= getSetOfCadbiomPossibilities(subEntity, dictPhysicalEntity)
	else:
		cadbiomPossibilities.add(dictPhysicalEntity[entity].cadbiomName)

	return cadbiomPossibilities


def addCadbiomSympyCondToReactions(dictReaction, dictPhysicalEntity):
	"""TODO !

	"""

	# Begin event's numeration from 1
	for event_number, (uri, reaction) in enumerate(dictReaction.iteritems(), 1):

		cadbiomSympyCond = None
		# set of Control objects
		for control in reaction.controllers:
			cadbiomPossibilities = getSetOfCadbiomPossibilities(control.controller, dictPhysicalEntity)

			if control.controlType == "ACTIVATION" :
				subCadbiomSympyCond = sympy.Or(sympy.Symbol(cadbiomPossibilities.pop()))
				for cadbiom in cadbiomPossibilities:
					subCadbiomSympyCond = sympy.Or(subCadbiomSympyCond,sympy.Symbol(cadbiom))

			elif control.controlType == "INHIBITION":
				subCadbiomSympyCond = sympy.Not(sympy.Symbol(cadbiomPossibilities.pop()))
				for cadbiom in cadbiomPossibilities:
					subCadbiomSympyCond = sympy.Or(subCadbiomSympyCond,sympy.Not(sympy.Symbol(cadbiom)))

			if cadbiomSympyCond ==  None:
				cadbiomSympyCond = subCadbiomSympyCond
			else:
				cadbiomSympyCond = sympy.And(cadbiomSympyCond, subCadbiomSympyCond)

		if cadbiomSympyCond ==  None:
			reaction.cadbiomSympyCond = sympy.sympify(True)
		else:
			reaction.cadbiomSympyCond = cadbiomSympyCond

		reaction.event = "_h_" + str(event_number)


def getListOfPossibilitiesAndCadbiomNames(entity, dictPhysicalEntity):
	listOfEquivalentsAndCadbiomName = []

	if len(dictPhysicalEntity[entity].listOfFlatComponents) != 0:
		for i in range(len(dictPhysicalEntity[entity].listOfFlatComponents)):
			flatComponents = dictPhysicalEntity[entity].listOfFlatComponents[i]
			cadbiomName = dictPhysicalEntity[entity].listOfCadbiomNames[i]
			listOfEquivalentsAndCadbiomName.append((flatComponents,cadbiomName))

	elif len(dictPhysicalEntity[entity].members) != 0 and dictPhysicalEntity[entity].membersUsed:
		for subEntity in dictPhysicalEntity[entity].members:
			listOfEquivalentsAndCadbiomName += getListOfPossibilitiesAndCadbiomNames(subEntity, dictPhysicalEntity)
	else:
		listOfEquivalentsAndCadbiomName.append((tuple([entity]),dictPhysicalEntity[entity].cadbiomName))

	return listOfEquivalentsAndCadbiomName


def refInCommon(entities1, entities2, dictPhysicalEntity):
	if len(set(entities1)&set(entities2)) > 0 : return True

	entityRefs1 = set()
	for entity in entities1:
		entityRef = dictPhysicalEntity[entity].entityRef
		if entityRef != None and entityRef != set():
			entityRefs1.add(entityRef)
	entityRefs2 = set()
	for entity in entities2:
		entityRef = dictPhysicalEntity[entity].entityRef
		if entityRef != None and entityRef != set():
			entityRefs2.add(entityRef)

	return (len(entityRefs1&entityRefs2) > 0)


def getProductCadbioms(entities, entityToListOfEquivalentsAndCadbiomName):
	listOfCadbioms = []
	for entity in entities:
		cadbioms = []
		for equis,cadbiom in entityToListOfEquivalentsAndCadbiomName[entity]:
			cadbioms.append(cadbiom)
		listOfCadbioms.append(cadbioms)

	return itertools.product(*listOfCadbioms)


def getProductCadbiomsMatched(entities, entityToListOfEquivalentsAndCadbiomName, entityToEntitiesMatched):
	listOfCadbioms = []
	for entity in entities:
		if entityToEntitiesMatched[entity] != set():
			cadbioms = []
			for equis,cadbiom in entityToListOfEquivalentsAndCadbiomName[entity]:
				cadbioms.append(cadbiom)
			listOfCadbioms.append(cadbioms)

	return itertools.product(*listOfCadbioms)


def getEntityNameUnmatched(entities, entityToEntitiesMatched, dictPhysicalEntity):
	nameUnmatched = set()
	for entity in entities:
		if entityToEntitiesMatched[entity] == set():
			nameUnmatched.add(dictPhysicalEntity[entity].cadbiomName)
	return nameUnmatched


def updateTransitions(reaction, dictPhysicalEntity, dictReaction, dictTransition):
	leftEntities = dictReaction[reaction].leftComponents
	rightEntities = dictReaction[reaction].rightComponents

	entityToListOfEquivalentsAndCadbiomName = {}
	for entity in leftEntities|rightEntities:
		entityToListOfEquivalentsAndCadbiomName[entity] = getListOfPossibilitiesAndCadbiomNames(entity, dictPhysicalEntity)

	cadbiomToCadbiomsMatched = defaultdict(set)
	entityToEntitiesMatched = defaultdict(set)
	match = False
	for entity1, entity2 in itertools.combinations(entityToListOfEquivalentsAndCadbiomName.keys(),2):
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
		if len(dictPhysicalEntity[entity].members) > 1 and dictPhysicalEntity[entity].membersUsed:
			presenceOfMembers = True
			break

	subDictTransition = defaultdict(list)
	subH = 1

	if not match or not presenceOfMembers:
		for productCadbiomsL in getProductCadbioms(leftEntities, entityToListOfEquivalentsAndCadbiomName):
			for productCadbiomsR in getProductCadbioms(rightEntities, entityToListOfEquivalentsAndCadbiomName):
				for cadbiomL, cadbiomR in itertools.product(productCadbiomsL,productCadbiomsR):
					transitionSympyCond = dictReaction[reaction].cadbiomSympyCond
					for otherCadbiomL in set(productCadbiomsL)-set([cadbiomL]):
						sympySymbol = sympy.Symbol(otherCadbiomL)
						transitionSympyCond = sympy.And(transitionSympyCond, sympySymbol)

					subDictTransition[(cadbiomL,cadbiomR)].append({
						'event': dictReaction[reaction].event+"_"+str(subH),
						'reaction': reaction,
						'sympyCond': transitionSympyCond
					})
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

					for cadbiomL, cadbiomR in itertools.product(productCadbiomsL,cadbiomsR):
						transitionSympyCond = dictReaction[reaction].cadbiomSympyCond
						for otherCadbiomL in set(productCadbiomsL)-set([cadbiomL]):
							sympySymbol = sympy.Symbol(otherCadbiomL)
							transitionSympyCond = sympy.And(transitionSympyCond, sympySymbol)

						subDictTransition[(cadbiomL,cadbiomR)].append({
							'event': dictReaction[reaction].event+"_"+str(subH),
							'reaction': reaction,
							'sympyCond': transitionSympyCond
						})
					subH += 1

		for entityR in rightEntities:
			if entityToEntitiesMatched[entityR] == set():
				nameEntityR = dictPhysicalEntity[entityR].cadbiomName
				for subEquis,subCadbiom in entityToListOfEquivalentsAndCadbiomName[entityR]:
					transitionSympyCond = dictReaction[reaction].cadbiomSympyCond

					subDictTransition[(nameEntityR,subCadbiom)].append({
						'event': dictReaction[reaction].event+"_"+str(subH),
						'reaction': reaction,
						'sympyCond': transitionSympyCond
					})
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

							subDictTransition[(cadbiomL,right)].append({
								'event': transition['event'],
								'reaction': reaction,
								'sympyCond': transitionSympyCond
							})

	for left,right in subDictTransition.keys():
		for transition in subDictTransition[(left,right)]:
			if subH > 2:
				event = transition['event']
			else:
				event = dictReaction[reaction].event

			dictTransition[(left,right)].append({
				'event': event,
				'reaction': reaction,
				'sympyCond': transition['sympyCond']
			})



def getTransitions(dictReaction, dictPhysicalEntity):
	"""

	"""

	def update_transitions(transitions, left_entity, right_entity, reaction):
		""".. todo: Move this function and reuse it elsewhere.
		"""

		transitions[(left_entity, right_entity)].append(
			{
				'event': reaction.event,
				'reaction': reaction.idReaction,
				'sympyCond': reaction.cadbiomSympyCond
			}
		)


	dictTransition = defaultdict(list)

	for reaction_uri, reaction in dictReaction.iteritems():

		typeName = reaction.reactiontype

		if typeName in ["BiochemicalReaction", "ComplexAssembly", "Transport",
			"TransportWithBiochemicalReaction"]:
			# ATTENTION: que faire si 'leftComponents'
			# ou bien 'rightComponents' sont vides ?
			# /!\ This modifies dictTransition in place
			updateTransitions(
				reaction_uri, dictPhysicalEntity, dictReaction, dictTransition
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
					dictTransition, cadbiomL, "#TRASH", reaction
				)

		elif typeName == "TemplateReaction":
			# Reaction of transcription
			# In Cadbiom language: Gene => product of gene
			entityR = reaction.productComponent
			# Sometimes, there is no entityR
			# ex: http://pathwaycommons.org/pc2/#TemplateReaction_3903f25156da4c9000a93bbc85b18572).
			# It is a bug in BioPax.
			if entityR != None:
				cadbiomR = dictPhysicalEntity[entityR].cadbiomName

				# /!\ This modifies dictTransition in place
				update_transitions(
					dictTransition, cadbiomR + "_gene", cadbiomR, reaction
				)

		elif typeName in ["Catalysis", "Control", "TemplateReactionRegulation"]:
			continue

		else:
			LOGGER.error("UNEXCEPTED REACTION: " + str(reaction_uri))

	return dictTransition


def filter_control(controls, pathways_names):
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

	return {control: controls[control] for control in controls
			if controls[control].controller not in pathways_names}


def main(params):
	"""Entry point"""

	if not os.path.isfile(params['pickleBackup']):

		dictPhysicalEntity = query.getPhysicalEntities(params['listOfGraphUri'])
		dictReaction	   = query.getReactions(params['listOfGraphUri'])
		dictLocation	   = query.getLocations(params['listOfGraphUri'])
		dictPathwayName = query.getPathways(params['listOfGraphUri'])
		dictControl = \
			filter_control(
				query.getControls(params['listOfGraphUri']),
				dictPathwayName,
			)

		addReactionToEntities(dictReaction, dictControl, dictPhysicalEntity)

		detectMembersUsedInEntities(dictPhysicalEntity, params['convertFullGraph'])
		developComplexs(dictPhysicalEntity)
		addControllersToReactions(dictReaction, dictControl)
		numerotateLocations(dictLocation, params['fullCompartmentsNames'])
		addCadbiomNameToEntities(dictPhysicalEntity, dictLocation)
		addCadbiomSympyCondToReactions(dictReaction, dictPhysicalEntity)

		dill.dump(
			[
				dictPhysicalEntity, dictReaction, dictControl, dictLocation,
			],
			open(params['pickleBackup'], "wb")
		)

	else:
		dictPhysicalEntity, dictReaction, dictControl, dictLocation = \
			dill.load(open(params['pickleBackup'], "rb"))

	dictTransition = getTransitions(dictReaction, dictPhysicalEntity)

	createCadbiomFile(
		dictTransition,
		dictPhysicalEntity,
		params['cadbiomFile'].rsplit('/', 1)[-1].rsplit('.', 1)[0], # model name
		params['cadbiomFile'] # path
	)
