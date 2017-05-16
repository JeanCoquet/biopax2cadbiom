# -*- coding: utf-8 -*-
"""
This module is used to translate biopax to a cadbiom model
"""

import sys, itertools, copy, pickle
import sparql_biopaxQueries as query
from collections import defaultdict
import networkx as nx
import xml.etree.ElementTree as ET
import sympy

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
			entity = dictReaction[reaction]['productComponent']
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

# TODO: Test this function
def developComplexs(dictPhysicalEntity):
	"""This procedure adds the key 'listOfFlatComponents' to the dictionnary dictPhysicalEntity[entity]. The value corresponds to a list of component sets. 
	
	:param dictPhysicalEntity: the dictionnary of biopax physicalEntities created by the function query.getPhysicalEntities()
	:type dictPhysicalEntity: dict
	"""
	for entity in dictPhysicalEntity:
		typeName = dictPhysicalEntity[entity]['type'].rsplit("#", 1)[1]
		if typeName == "Complex":
			if len(dictPhysicalEntity[entity]['listOfFlatComponents']) == 0:
				developComplexEntity(entity, dictPhysicalEntity)


def developComplexEntity(complexEntity, dictPhysicalEntity):
	"""This procedure fills the value of dictPhysicalEntity[entity]['listOfFlatComponents']. 
	
	:param complexEntity: the biopax id of a complex entity
	:param dictPhysicalEntity: the dictionnary of biopax physicalEntities created by the function query.getPhysicalEntities()
	:type complexEntity: string
	:type dictPhysicalEntity: dict
	"""
	listOfFlatComponents = list()
	for component in dictPhysicalEntity[complexEntity]['components']:
		typeName = dictPhysicalEntity[component]['type'].rsplit("#", 1)[1]
		if typeName == "Complex":
			if len(dictPhysicalEntity[component]['listOfFlatComponents']) == 0:
				developComplexEntity(component, dictPhysicalEntity)
			listOfFlatComponents.append(dictPhysicalEntity[component]['listOfFlatComponents'])
		elif len(dictPhysicalEntity[component]['members']) != 0 and dictPhysicalEntity[component]['membersUsed']:
			listOfFlatComponents.append(list(dictPhysicalEntity[component]['members']))
		else:
			listOfFlatComponents.append([component])
	
	if len(listOfFlatComponents) != 0:
		dictPhysicalEntity[complexEntity]['listOfFlatComponents'] = []
		for elements in itertools.product(*listOfFlatComponents):
			l = []
			for e in elements: 
				if isinstance(e, tuple): l += e
				else: l.append(e)
			dictPhysicalEntity[complexEntity]['listOfFlatComponents'].append(tuple(l))

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
	
	for entity in dictPhysicalEntity:
		dictPhysicalEntity[entity]['listOfCadiomNames'] = []
		if len(dictPhysicalEntity[entity]['listOfFlatComponents']) == 1:
			dictPhysicalEntity[entity]['listOfCadiomNames'].append(dictPhysicalEntity[entity]['cadbiomName'])
		else:
			for flatComponents in dictPhysicalEntity[entity]['listOfFlatComponents']:
				s = "_".join(dictPhysicalEntity[subEntity]['cadbiomName'] for subEntity in flatComponents)
				dictPhysicalEntity[entity]['listOfCadiomNames'].append(s)
	
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
	if synonym == None: name = dictPhysicalEntity[entity]['name']
	else: name = synonym
	location = dictPhysicalEntity[entity]['location']
	locationId = dictLocation[location]['cadbiomId']
	return name.replace(' ','_')+"_"+locationId

def getListOfCadbiomPossibilities(entity, dictPhysicalEntity):
	cadbiomPossibilities = set()
	typeName = dictPhysicalEntity[entity]['type'].rsplit("#", 1)[1]
	if len(dictPhysicalEntity[entity]['listOfFlatComponents']) != 0:
		cadbiomPossibilities = set(dictPhysicalEntity[entity]['listOfCadiomNames'])
	elif len(dictPhysicalEntity[entity]['members']) != 0:
		for subEntity in dictPhysicalEntity[entity]['members']:
			cadbiomPossibilities.add(dictPhysicalEntity[subEntity]['cadbiomName'])
	else:
		cadbiomPossibilities.add(dictPhysicalEntity[entity]['cadbiomName'])
	return cadbiomPossibilities

def addCadbiomSympyCondToReactions(dictReaction, dictPhysicalEntity):
	for reaction in dictReaction:
		controllers = dictReaction[reaction]['controllers']
		
		cadbiomSympyCond = None
		for entity, controlType in controllers:
			cadbiomPossibilities = getListOfCadbiomPossibilities(entity, dictPhysicalEntity)
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
		
		if cadbiomSympyCond ==  None: dictReaction[reaction]['cadbiomSympyCond'] = ""
		else: dictReaction[reaction]['cadbiomSympyCond'] = sympy.simplify_logic(cadbiomSympyCond)


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


def getTransitions(dictReaction, dictPhysicalEntity):
	dictTransition = defaultdict(lambda: defaultdict(list))
	
	for reaction in reactionToEventAndCond:
		typeName = dictReaction[reaction]['type'].rsplit("#", 1)[1]
		
		if typeName == "BiochemicalReaction" :
			for entityL in dictReaction[reaction]['leftComponents']:
				for entityR in dictReaction[reaction]['rightComponents']:
					addTransition(dictTransition, entityL, entityR, reaction, dictPhysicalEntity, reactionToEventAndCond)
					
		elif typeName == "Degradation":
			for entityL in dictReaction[reaction]['leftComponents']:
					addTransition(dictTransition, entityL, "", reaction, dictPhysicalEntity, reactionToEventAndCond)
		
		elif typeName == "TemplateReaction":
			addTransition(dictTransition, "", dictReaction[reaction]['productComponent'], reaction, dictPhysicalEntity, reactionToEventAndCond)
	
	return dictTransition

#"""
#Attiention pb, tu fais le produit cartesien entre les genes et les proteines alors qu ils sont associes
#"""
#def addTransition(dictTransition, entityL, entityR, reaction, dictPhysicalEntity, reactionToEventAndCond):
	#cadbiomsL, cadbiomsR = set(),set()
	
	#if entityL != "": 
		#if len(dictPhysicalEntity[entityL]['members']) == 0:
			#cadbiomsL.add(dictPhysicalEntity[entityL]['cadbiomName'])
		#else:
			#for subEntityL in dictPhysicalEntity[entityL]['members']:
				#cadbiomsL.add(dictPhysicalEntity[subEntityL]['cadbiomName'])
	#else: 
		#if len(dictPhysicalEntity[entityR]['members']) == 0:
			#cadbiomsL.add("gene_"+dictPhysicalEntity[entityR]['cadbiomName'])
		#else:
			#for subEntityR in dictPhysicalEntity[entityR]['members']:
				#cadbiomsL.add("gene_"+dictPhysicalEntity[subEntityR]['cadbiomName'])
	
	#if entityR != "": 
		#if len(dictPhysicalEntity[entityR]['members']) == 0:
			#cadbiomsR.add(dictPhysicalEntity[entityR]['cadbiomName'])
		#else:
			#for subEntityR in dictPhysicalEntity[entityR]['members']:
				#cadbiomsR.add(dictPhysicalEntity[subEntityR]['cadbiomName'])
	#else: 
		#cadbiomsR.add("#TRASH")
	
	#if len(cadbiomsL) == 1 and len(cadbiomsR) == 1:
		#cadbiomL, cadbiomR = cadbiomsL.pop(), cadbiomsR.pop()
		#dictTransition[(cadbiomL,cadbiomR)]['reactions'].append(reaction)
		#dictTransition[(cadbiomL,cadbiomR)]['eventAndCond'].append(reactionToEventAndCond[reaction])
	#else:
		#event, cond = reactionToEventAndCond[reaction]
		#i = 1
		#for cadbiomL in cadbiomsL:
			#for cadbiomR in cadbiomsR:
				#dictTransition[(cadbiomL,cadbiomR)]['reactions'].append(reaction)
				#dictTransition[(cadbiomL,cadbiomR)]['eventAndCond'].append((event+"."+str(i),cond))
				#i += 1

#def createCadbiomFile(dictTransition, dictPhysicalEntity, nameModel, filePath):
	#model = ET.Element("model", xmlns="http://cadbiom", name=nameModel)
	
	#for entity in dictPhysicalEntity:
		#if len(dictPhysicalEntity[entity]['members']) == 0:
			#cadbiomName = dictPhysicalEntity[entity]['cadbiomName']
			#ET.SubElement(model, "CSimpleNode", name=cadbiomName, xloc="0.0", yloc="0.0")
	
	#for cadbiomL,cadbiomR in dictTransition:
		#for i in range(len(dictTransition[(cadbiomL,cadbiomR)]['eventAndCond'])):
			#event, cond = dictTransition[(cadbiomL,cadbiomR)]['eventAndCond'][i]
			#reaction = dictTransition[(cadbiomL,cadbiomR)]['reactions'][i]
			#ET.SubElement(model, "transition", ori=cadbiomL, ext=cadbiomR, event=event, condition=cond, action="", fact_ids="[]").text = "reaction = "+reaction
	
	#tree = ET.ElementTree(model)
	#tree.write(filePath)

if __name__ == "__main__" :
	listOfGraphUri = sys.argv[1:]
	
	dictPhysicalEntity = query.getPhysicalEntities(listOfGraphUri)	
	dictReaction = query.getReactions(listOfGraphUri)
	dictControl = query.getControls(listOfGraphUri)
	dictLocation = query.getLocations(listOfGraphUri)
	
	addReactionToEntities(dictReaction, dictControl, dictPhysicalEntity)
	detectMembersUsedInEntities(dictPhysicalEntity)
	developComplexs(dictPhysicalEntity)
	addControllersToReactions(dictReaction, dictControl)
	idLocationToLocation = numerotateLocations(dictLocation)
	cadbiomNameToPhysicalEntity = addCadbiomNameToEntities(dictPhysicalEntity, dictLocation)
	addCadbiomSympyCondToReactions(dictReaction, dictPhysicalEntity)
	
	#addEventAndCondToReactions(dictReaction, dictPhysicalEntity)
	#dictTransition = getTransitions(dictReaction, dictPhysicalEntity)
	
