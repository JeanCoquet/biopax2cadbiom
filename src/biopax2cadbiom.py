# -*- coding: utf-8 -*-
"""
This module is used to translate biopax to a cadbiom model
"""

from __future__ import print_function

# Standard imports
import itertools, copy, dill, sympy, os, sys, re
from collections import defaultdict
import networkx as nx
from lxml import etree as ET

# Custom imports
from src import sparql_biopaxQueries as query


def addReactionToEntities(dictReaction, dictControl, dictPhysicalEntity):
	"""This procedure adds the key 'reactions' to the dictionnary dictPhysicalEntity[entity]. The value corresponds to a set of reactions involving entity.

	:param dictReaction: the dictionnary of biopax reactions created by the function query.getReactions()
	:param dictControl: the dictionnary of biopax controls created by the function query.getControls()
	:param dictPhysicalEntity: the dictionnary of biopax physicalEntities created by the function query.getPhysicalEntities()
	:type dictReaction: dict
	:type dictControl: dict
	:type dictPhysicalEntity: dict
	"""
	for reaction in dictReaction:
		if dictReaction[reaction].productComponent != None:
			entity = dictReaction[reaction].productComponent
			dictPhysicalEntity[entity].reactions.add(reaction)
		if dictReaction[reaction].participantComponent != None:
			entity = dictReaction[reaction].participantComponent
			dictPhysicalEntity[entity].reactions.add(reaction)
		for entity in dictReaction[reaction].leftComponents | dictReaction[reaction].rightComponents:
			dictPhysicalEntity[entity].reactions.add(reaction)

	for control in dictControl:
		entity = dictControl[control].controller
		reaction = dictControl[control].reaction
		if entity != None and reaction != None:
			dictPhysicalEntity[entity].reactions.add(reaction)


def detectMembersUsedInEntities(dictPhysicalEntity, convertFullGraph):
	"""This procedure adds the key 'membersUsed' to the dictionnary dictPhysicalEntity[entity]. The value is False if the entity does not have members or if at least one member is involved in a reaction, eles the value is True.

	:param dictPhysicalEntity: the dictionnary of biopax physicalEntities created by the function query.getPhysicalEntities()
	:param convertFullGraph: convert all entities to cadbiom node, even the entities not used
	:type dictPhysicalEntity: dict
	:type convertFullGraph: boolean
	"""
	for entity in dictPhysicalEntity:
		if convertFullGraph:
			dictPhysicalEntity[entity].membersUsed = True
		else:
			dictPhysicalEntity[entity].membersUsed = False
			for subEntity in dictPhysicalEntity[entity].members:
				if subEntity in dictPhysicalEntity: # IL PEUT Y AVOIR DES ENTITY NON REFERENCEE (EX: http://www.reactome.org/biopax/60/48887#Complex5918)
					if len(dictPhysicalEntity[subEntity].reactions) != 0:
						dictPhysicalEntity[entity].membersUsed = True
					break


# TODO: Test this function
def developComplexs(dictPhysicalEntity):
	"""This procedure adds the key 'listOfFlatComponents' to the dictionnary dictPhysicalEntity[entity]. The value corresponds to a list of component sets. 

	:param dictPhysicalEntity: the dictionnary of biopax physicalEntities created by the function query.getPhysicalEntities()
	:type dictPhysicalEntity: dict
	"""
	for entity in dictPhysicalEntity:
		if dictPhysicalEntity[entity].entityType != set() :
			typeName = dictPhysicalEntity[entity].entityType.rsplit("#", 1)[1]
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
			typeName = dictPhysicalEntity[component].entityType.rsplit("#", 1)[1]
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
	"""This procedure adds the key 'controllers' to the dictionnary dictReaction[reaction]. The value corresponds to a set of controller entities involved in reaction.

	:param dictReaction: the dictionnary of biopax reactions created by the function query.getReactions()
	:param dictControl: the dictionnary of biopax controls created by the function query.getControls()
	:type dictReaction: dict
	:type dictControl: dict
	"""
	for control in dictControl:
		reaction = dictControl[control].reaction
		physicalEntity = dictControl[control].controller
		if reaction != None and physicalEntity != None:
			if reaction in dictReaction:
				dictReaction[reaction].controllers.add((physicalEntity,dictControl[control].controlType))

def numerotateLocations(dictLocation):
	"""This function creates an cadbiom ID for each location. It adds the key 'cadbiomId' to the dictionnary dictLocation[location].

	:param dictLocation: the dictionnary of biopax reactions created by the function query.getLocations()
	:type dictLocation: dict
	:returns: idLocationToLocation
	:rtype: dict
	"""
	idLocationToLocation = {}

	currentId = 0
	for location in sorted(dictLocation.keys()):
		idLocationToLocation[str(currentId)] = location
		dictLocation[location].cadbiomId = str(currentId)
		currentId += 1

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
	nbEvent = 1
	for reaction in dictReaction:
		controllers = dictReaction[reaction].controllers

		cadbiomSympyCond = None
		for entity, controlType in controllers:
			cadbiomPossibilities = getSetOfCadbiomPossibilities(entity, dictPhysicalEntity)
			if controlType == "ACTIVATION" :
				subCadbiomSympyCond = sympy.Or(sympy.Symbol(cadbiomPossibilities.pop()))
				for cadbiom in cadbiomPossibilities:
					subCadbiomSympyCond = sympy.Or(subCadbiomSympyCond,sympy.Symbol(cadbiom))
			elif controlType == "INHIBITION":
				subCadbiomSympyCond = sympy.Not(sympy.Symbol(cadbiomPossibilities.pop()))
				for cadbiom in cadbiomPossibilities:
					subCadbiomSympyCond = sympy.Or(subCadbiomSympyCond,sympy.Not(sympy.Symbol(cadbiom)))

			if cadbiomSympyCond ==  None: cadbiomSympyCond = subCadbiomSympyCond
			else: cadbiomSympyCond = sympy.And(cadbiomSympyCond, subCadbiomSympyCond)

		if cadbiomSympyCond ==  None: dictReaction[reaction].cadbiomSympyCond = sympy.sympify(True)
		else: dictReaction[reaction].cadbiomSympyCond = cadbiomSympyCond

		dictReaction[reaction].event = "_h_"+str(nbEvent)
		nbEvent += 1


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
	dictTransition = defaultdict(list)

	for reaction in dictReaction:
		typeName = dictReaction[reaction].reactiontype.rsplit("#", 1)[1]

		if typeName in ["BiochemicalReaction", "ComplexAssembly", "Transport"]:
			#ATTENTION: que faire si 'leftComponents' ou bien 'rightComponents' sont vides ?
			updateTransitions(reaction, dictPhysicalEntity, dictReaction, dictTransition)

		elif typeName == "Degradation":
			for entityL in dictReaction[reaction].leftComponents: # Normally there is just one component
				cadbiomL = dictPhysicalEntity[entityL].cadbiomName
				dictTransition[(cadbiomL,"#TRASH")].append({
					'event': dictReaction[reaction].event,
					'reaction': reaction,
					'sympyCond': dictReaction[reaction].cadbiomSympyCond
				})

		elif typeName == "TemplateReaction":
			entityR = dictReaction[reaction].productComponent
			cadbiomR = dictPhysicalEntity[entityR].cadbiomName
			dictTransition[(cadbiomR+"_gene",cadbiomR)].append({
				'event': dictReaction[reaction].event,
				'reaction': reaction,
				'sympyCond': dictReaction[reaction].cadbiomSympyCond
			})

		elif typeName == "Catalysis" or typeName == "Control":
			continue

		else:
			print("UNEXCEPTED REACTION: "+reaction, file=sys.stderr)

	return dictTransition


def formatCadbiomSympyCond(cadbiomSympyCond):
	if cadbiomSympyCond == True:
		return ''
	elif type(cadbiomSympyCond) == sympy.Or:
		return "("+" or ".join([formatCadbiomSympyCond(arg) for arg in cadbiomSympyCond.args])+")"
	elif type(cadbiomSympyCond) == sympy.And:
		return "("+" and ".join([formatCadbiomSympyCond(arg) for arg in cadbiomSympyCond.args])+")"
	elif type(cadbiomSympyCond) == sympy.Not:
		subCadbiomStrCond = formatCadbiomSympyCond(cadbiomSympyCond.args[0])
		if subCadbiomStrCond[0] == "(": return "not"+subCadbiomStrCond
		else: return "not("+subCadbiomStrCond+")"

	return str(cadbiomSympyCond)

def formatEventAndCond(setOfEventAndCond):
	event, cond = setOfEventAndCond.pop()
	s = "("+event+") when ("+formatCadbiomSympyCond(cond)+")"
	if len(setOfEventAndCond) == 0:
		return s
	else:
		return "("+s+") default ("+formatEventAndCond(setOfEventAndCond)+")"

def createCadbiomFile(dictTransition,
					  dictPhysicalEntity,
					  dictReaction,
					  nameModel,
					  filePath):
	model = ET.Element("model", xmlns="http://cadbiom", name=nameModel)

	cadbiomNodes = set()
	for cadbiomL,cadbiomR in dictTransition:
		cadbiomNodes.add(cadbiomL)
		cadbiomNodes.add(cadbiomR)
		for transition in dictTransition[(cadbiomL,cadbiomR)]:
			cadbiomNodes |= set([str(atom) for atom in transition['sympyCond'].atoms()])

	for cadbiomName in cadbiomNodes:
		ET.SubElement(model, "CSimpleNode", name=cadbiomName, xloc="0.0", yloc="0.0")

	for cadbiomL,cadbiomR in dictTransition:
		if len(dictTransition[(cadbiomL,cadbiomR)]) == 1:
			transition = dictTransition[(cadbiomL,cadbiomR)][0]
			ET.SubElement(
				model, "transition",
				ori=cadbiomL, ext=cadbiomR,
				event=transition["event"], condition=formatCadbiomSympyCond(transition["sympyCond"]),
				action="", fact_ids="[]").text = "reaction = "+transition["reaction"]
		else:
			setOfEventAndCond = set([])
			for transition in dictTransition[(cadbiomL,cadbiomR)]:
				setOfEventAndCond.add((transition["event"],transition["sympyCond"]))
			eventAndCondStr = formatEventAndCond(setOfEventAndCond)
			ET.SubElement(
				model, "transition",
				ori=cadbiomL, ext=cadbiomR,
				event=eventAndCondStr, condition="",
				action="", fact_ids="[]").text = "reaction = "+transition["reaction"]

	tree = ET.ElementTree(model)
	tree.write(filePath, pretty_print=True)


def main(args):

	if not os.path.isfile(args.pickleBackup):

		dictPhysicalEntity = query.getPhysicalEntities(args.listOfGraphUri)
		dictReaction = query.getReactions(args.listOfGraphUri)
		dictControl = query.getControls(args.listOfGraphUri)
		dictLocation = query.getLocations(args.listOfGraphUri)

		addReactionToEntities(dictReaction, dictControl, dictPhysicalEntity)
		detectMembersUsedInEntities(dictPhysicalEntity, args.convertFullGraph)
		developComplexs(dictPhysicalEntity)
		addControllersToReactions(dictReaction, dictControl)
		idLocationToLocation = numerotateLocations(dictLocation)
		cadbiomNameToPhysicalEntity = addCadbiomNameToEntities(dictPhysicalEntity, dictLocation)
		addCadbiomSympyCondToReactions(dictReaction, dictPhysicalEntity)

		dill.dump(
			[
				dictPhysicalEntity, dictReaction, dictControl, dictLocation,
				idLocationToLocation, cadbiomNameToPhysicalEntity
			],
			open(args.pickleBackup, "wb")
		)

	else:
		dictPhysicalEntity, dictReaction, dictControl, \
		dictLocation, idLocationToLocation, cadbiomNameToPhysicalEntity \
			= dill.load(open(args.pickleBackup, "rb"))

	dictTransition = getTransitions(dictReaction, dictPhysicalEntity)

	cadbiomModelName = args.cadbiomFile.rsplit('/',1)[-1].rsplit('.',1)[0]
	createCadbiomFile(
		dictTransition,
		dictPhysicalEntity,
		dictReaction,
		cadbiomModelName,
		args.cadbiomFile
	)
