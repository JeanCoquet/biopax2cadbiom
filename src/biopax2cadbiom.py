# -*- coding: utf-8 -*-
"""
This module is used to translate biopax to a cadbiom model
"""

import itertools, copy, dill, sympy, os
from src import sparql_biopaxQueries as query
from collections import defaultdict
import networkx as nx
#import xml.etree.ElementTree as ET
from lxml import etree as ET

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
		if dictReaction[reaction]['productComponent'] != None:
			entity = dictReaction[reaction]['productComponent']
			dictPhysicalEntity[entity]['reactions'].add(reaction)
		if dictReaction[reaction]['participantComponent'] != None:
			entity = dictReaction[reaction]['participantComponent']
			dictPhysicalEntity[entity]['reactions'].add(reaction)
		for entity in dictReaction[reaction]['leftComponents']|dictReaction[reaction]['rightComponents']:
			dictPhysicalEntity[entity]['reactions'].add(reaction)

	for control in dictControl:
		entity = dictControl[control]['controller']
		reaction = dictControl[control]['reaction']
		if entity != None and reaction != None:
			dictPhysicalEntity[entity]['reactions'].add(reaction)


def detectMembersUsedInEntities(dictPhysicalEntity):
	"""This procedure adds the key 'membersUsed' to the dictionnary dictPhysicalEntity[entity]. The value is False if the entity does not have members or if at least one member is involved in a reaction, eles the value is True.

	:param dictPhysicalEntity: the dictionnary of biopax physicalEntities created by the function query.getPhysicalEntities()
	:type dictPhysicalEntity: dict
	"""
	for entity in dictPhysicalEntity:
		dictPhysicalEntity[entity]['membersUsed'] = False
		for subEntity in dictPhysicalEntity[entity]['members']:
			if len(dictPhysicalEntity[subEntity]['reactions']) != 0:
				dictPhysicalEntity[entity]['membersUsed'] = True
				break

def addControllersToReactions(dictReaction, dictControl):
	"""This procedure adds the key 'controllers' to the dictionnary dictReaction[reaction]. The value corresponds to a set of controller entities involved in reaction.

	:param dictReaction: the dictionnary of biopax reactions created by the function query.getReactions()
	:param dictControl: the dictionnary of biopax controls created by the function query.getControls()
	:type dictReaction: dict
	:type dictControl: dict
	"""
	for control in dictControl:
		reaction = dictControl[control]['reaction']
		physicalEntity = dictControl[control]['controller']
		if reaction != None and physicalEntity != None:
			if reaction in dictReaction:
				dictReaction[reaction]['controllers'].add((physicalEntity,dictControl[control]['controlType']))

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
		dictLocation[location]['cadbiomId'] = str(currentId)
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
		physicalEntities.add(dictReaction[reaction]['productComponent'])
		physicalEntities.add(dictReaction[reaction]['participantComponent'])
		physicalEntities |= dictReaction[reaction]['leftComponents']
		physicalEntities |= dictReaction[reaction]['rightComponents']
		physicalEntities &= allPhysicalEntities

		for pathway in dictReaction[reaction]['pathways']:
			pathwayToPhysicalEntities[pathway] |= physicalEntities

	for control in dictControl:
		if dictControl[control]['controller'] in allPhysicalEntities:
			reaction = dictControl[control]['reaction']
			for pathway in dictReaction[reaction]['pathways']:
				pathwayToPhysicalEntities[pathway].add(dictControl[control]['controller'])

	return pathwayToPhysicalEntities


def createGraph(pathwayToName, pathwayToSuperPathways, pathwayToPhysicalEntities, dictPhysicalEntity, pathGexfFile):
	G = nx.Graph()
	for pathway in pathwayToName:
		s = pathwayToName[pathway]
		if len(pathwayToSuperPathways[pathway]) != 0: s = ""

		G.add_node(pathway, label=s, Type='pathway')
		for superPathway in pathwayToSuperPathways[pathway]:
			G.add_edge(superPathway, pathway, Type='Inclusion of pathway')

	for pathway1, pathway2 in itertools.combinations(pathwayToPhysicalEntities.keys(),2):
		physicalEntitiesShared = pathwayToPhysicalEntities[pathway1]&pathwayToPhysicalEntities[pathway2]

		shareProteinsOrComplexs = False
		for entity in physicalEntitiesShared:
			typeName = dictPhysicalEntity[entity]['type'].rsplit("#", 1)[1]
			if typeName == "Protein" or typeName == "Complex":
				shareProteinsOrComplexs = True
				break

		if shareProteinsOrComplexs:
			G.add_edge(pathway1, pathway2, Type='Sharing of physical entities')

	nx.write_gexf(G, pathGexfFile)


def addCadbiomNameToEntities(dictPhysicalEntity, dictLocation):
	"""This function creates the dictionnary cadbiomNameToPhysicalEntity, it adds the keys 'cadbiomName' and 'listOfCadiomNames' to the dictionnary dictPhysicalEntity[entity].
	The value of dictPhysicalEntity[entity]['cadbiomName'] corresponds to an unique cadbiom ID for the entity.
	The value of dictPhysicalEntity[entity]['listOfCadiomNames'] corresponds to a list if unique cadbiom IDs. Each member of the list is a unique cadbiom ID of each set of dictPhysicalEntity[entity]['listOfFlatComponents'].


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
			dictPhysicalEntity[entity]['cadbiomName'] = cadbiomName
		else:
			entities = cadbiomNameToPhysicalEntities[cadbiomName]
			entityToUniqueSynonym = findUniqueSynonym(entities, dictPhysicalEntity)
			for entity in entities:
				cadbiomName = getCadbiomName(entity, dictPhysicalEntity, dictLocation, synonym=entityToUniqueSynonym[entity])
				cadbiomNameToPhysicalEntity[cadbiomName] = entity
				dictPhysicalEntity[entity]['cadbiomName'] = cadbiomName

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
				entityToUniqueSynonyms[entity] = copy.copy(dictPhysicalEntity[entity]['synonyms'])
		for entity1,entity2 in itertools.combinations(entityToUniqueSynonyms.keys(),2):
			entityToUniqueSynonyms[entity1] -= dictPhysicalEntity[entity2]['synonyms']
			entityToUniqueSynonyms[entity2] -= dictPhysicalEntity[entity1]['synonyms']

		nbEntitiesSelected = 0
		for entity in entityToUniqueSynonyms:
			if len(entityToUniqueSynonyms[entity]) > 0:
				entityToUniqueSynonym[entity] = dictPhysicalEntity[entity]['name']+"_("+entityToUniqueSynonyms[entity].pop()+")"
				nbEntitiesSelected += 1

		if nbEntitiesSelected == 0:
			vI = 1
			for entity in entityToUniqueSynonyms:
				entityToUniqueSynonym[entity] = dictPhysicalEntity[entity]['name']+"_(v"+str(vI)+")"
				vI += 1

	return entityToUniqueSynonym


def getCadbiomName(entity, dictPhysicalEntity, dictLocation, synonym=None):
	if synonym == None:
		name = dictPhysicalEntity[entity]['name']
	else:
		name = synonym

	location = dictPhysicalEntity[entity]['location']
	if location != None:
		locationId = dictLocation[location]['cadbiomId']
		return name.replace(' ','_')+"_"+locationId
	else:
		return name.replace(' ','_')


def addCadbiomSympyCondToReactions(dictReaction, dictPhysicalEntity):
	nbEvent = 0
	for reaction in dictReaction:
		controllers = dictReaction[reaction]['controllers']

		cadbiomSympyCond = sympy.sympify(True)
		for entity, controlType in controllers:
			sympySymbol = sympy.Symbol(dictPhysicalEntity[entity]['cadbiomName'])
			if controlType == "ACTIVATION" :
				cadbiomSympyCond = sympy.And(cadbiomSympyCond, sympySymbol)
			elif controlType == "INHIBITION":
				cadbiomSympyCond = sympy.And(cadbiomSympyCond, sympy.Not(sympySymbol))

		dictReaction[reaction]['cadbiomSympyCond'] = cadbiomSympyCond
		dictReaction[reaction]['event'] = "h_"+str(nbEvent)
		nbEvent += 1


def getTransitions(dictReaction, dictPhysicalEntity):
	dictTransition = defaultdict(lambda: defaultdict(set))

	for reaction in sorted(list(dictReaction.keys()))[:100]:
		typeName = dictReaction[reaction]['type'].rsplit("#", 1)[1].split('_',1)[0]

		if typeName == "BiochemicalReaction" :
			for entityL in dictReaction[reaction]['leftComponents']:
				for entityR in dictReaction[reaction]['rightComponents']:

					transitionSympyCond = dictReaction[reaction]['cadbiomSympyCond']
					for otherEntityL in dictReaction[reaction]['leftComponents']-set([entityL]):
						sympySymbol = sympy.Symbol(dictPhysicalEntity[otherEntityL]['cadbiomName'])
						transitionSympyCond = sympy.And(transitionSympyCond, sympySymbol)

					cadbiomL = dictPhysicalEntity[entityL]['cadbiomName']
					cadbiomR = dictPhysicalEntity[entityR]['cadbiomName']
					dictTransition[(cadbiomL,cadbiomR)]['reactionAndSympyCond'].add((reaction,transitionSympyCond))

		if typeName == "Degradation":
			for entityL in dictReaction[reaction]['leftComponents']: # Normally there is just one component
				cadbiomL = dictPhysicalEntity[entityL]['cadbiomName']
				dictTransition[(cadbiomL,"#TRASH")]['reactionAndSympyCond'].add((reaction,dictReaction[reaction]['cadbiomSympyCond']))

		elif typeName == "TemplateReaction":
			entityR = dictReaction[reaction]['productComponent']
			cadbiomR = dictPhysicalEntity[entityR]['cadbiomName']
			dictTransition[(cadbiomR+"_gene",cadbiomR)]['reactionAndSympyCond'].add((reaction,dictReaction[reaction]['cadbiomSympyCond']))

	return dictTransition


def formatCadbiomSympyCond(cadbiomSympyCond):
	if type(cadbiomSympyCond) == sympy.Or:
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

	for cadbiomName in cadbiomNodes:
		ET.SubElement(model, "CSimpleNode", name=cadbiomName, xloc="0.0", yloc="0.0")

	for cadbiomL,cadbiomR in dictTransition:
		if len(dictTransition[(cadbiomL,cadbiomR)]['reactionAndSympyCond']) == 1:
			reaction, cond = list(dictTransition[(cadbiomL,cadbiomR)]['reactionAndSympyCond'])[0]
			event = dictReaction[reaction]['event']
			ET.SubElement(
				model, "transition",
				ori=cadbiomL, ext=cadbiomR,
				event=event, condition=formatCadbiomSympyCond(cond),
				action="", fact_ids="[]").text = "reaction = "+reaction
		else:
			setOfEventAndCond = set([])
			for reaction, cond in dictTransition[(cadbiomL,cadbiomR)]['reactionAndSympyCond']:
				event = dictReaction[reaction]['event']
				setOfEventAndCond.add((event,cond))
			eventAndCondStr = formatEventAndCond(setOfEventAndCond)
			ET.SubElement(
				model, "transition",
				ori=cadbiomL, ext=cadbiomR,
				event=eventAndCondStr, condition="",
				action="", fact_ids="[]").text = "reaction = "+reaction

	tree = ET.ElementTree(model)
	tree.write(filePath, pretty_print=True)


def main(args):

	if not os.path.isfile(args.pickleBackup):

		dictPhysicalEntity = query.getPhysicalEntities(args.listOfGraphUri)
		dictReaction = query.getReactions(args.listOfGraphUri)
		dictControl = query.getControls(args.listOfGraphUri)
		dictLocation = query.getLocations(args.listOfGraphUri)

		addReactionToEntities(dictReaction, dictControl, dictPhysicalEntity)
		detectMembersUsedInEntities(dictPhysicalEntity)
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
