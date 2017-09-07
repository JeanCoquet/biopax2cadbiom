# -*- coding: utf-8 -*-
"""
This module is used to export biopax processed data to cabiom model file format.
"""
from __future__ import unicode_literals
from __future__ import print_function

# Standard imports
import sympy
from lxml import etree as ET

# Custom imports
from src import model_corrections as mc


def formatCadbiomSympyCond(cadbiomSympyCond):
	"""
	:return type: <str>
	"""

	if cadbiomSympyCond == True:
		return ''
	elif type(cadbiomSympyCond) == sympy.Or:
		return "("+" or ".join([formatCadbiomSympyCond(arg) for arg in cadbiomSympyCond.args])+")"
	elif type(cadbiomSympyCond) == sympy.And:
		return "("+" and ".join([formatCadbiomSympyCond(arg) for arg in cadbiomSympyCond.args])+")"
	elif type(cadbiomSympyCond) == sympy.Not:
		subCadbiomStrCond = formatCadbiomSympyCond(cadbiomSympyCond.args[0])
		if subCadbiomStrCond[0] == "(":
			return "not"+subCadbiomStrCond
		else:
			return "not("+subCadbiomStrCond+")"

	return str(cadbiomSympyCond)


def formatEventAndCond(setOfEventAndCond):
	"""
	:return type: <str>
	"""

	# remove and return an arbitrary element from s; raises KeyError if empty ?????????????????????
	event, cond = setOfEventAndCond.pop()
	condition_str = '({}) when ({})'.format(event, formatCadbiomSympyCond(cond))
	if len(setOfEventAndCond) == 0:
		return condition_str
	else:
		return '({}) default ({})'.format(condition_str,
										  formatEventAndCond(setOfEventAndCond))


def get_names_of_missing_physical_entities(dictPhysicalEntity):
	"""Get uri and cadbiom name for each entity in the model.

	:param: Dictionnary of uris as keys and PhysicalEntities as values.
	:type: <dict>
	:return: Dictionnary of names as keys and uris as values.
	:rtype: <dict>
	"""

	# We want uri and cadbiom name for each entity in the model
	# Get all names and their uris
	cadbiomNames = {entity.cadbiomName: entity.uri
						for entity in dictPhysicalEntity.values()}

	# Fix: Some components are created by our scripts
	# => ex: complexes with members involved that are classes
	# PS: classes are already in dictPhysicalEntity
	# PS: genes aren't in BioPAX format. getTransitions() from biopax2cadbiom
	# added these entities.
	cadbiomNames.update(
		{cadbiomNameWithMembers: entity.uri
			for entity in dictPhysicalEntity.values()
			for cadbiomNameWithMembers in entity.listOfCadbiomNames}
	)
	return cadbiomNames


def createCadbiomFile(dictTransition, dictPhysicalEntity, nameModel, filePath):
	"""Export data into a cadbiom model file format.

	:param arg1: Dictionnary of transitions and their respective set of events.
		.. example::
			subDictTransition[(cadbiomL,right)].append({
				'event': transition['event'],
				'reaction': reaction,
				'sympyCond': transitionSympyCond
			}
	:param arg2: Dictionnary of biopax physicalEntities,
		created by the function query.getPhysicalEntities()
	:param arg3: Name of the model.
	:param arg4: File path.
	:type arg1: <dict <tuple <str>, <str>>: <list <dict>>>
	:type arg2: <dict <str>: <PhysicalEntity>>
		keys: uris; values entity objects
	:type arg3: <str>
	:type arg4: <str>
	"""

	# Header
	model = ET.Element("model", xmlns="http://cadbiom.genouest.org/",
					   name=nameModel)

	# Get all nodes in transitions

	# Put these nodes in the model
	# PS: why we don't do that in the following iteration of dictTransition ?
	# Because the cadbiom model is parsed from the top to the end ><
	# If nodes are at the end, the model will fail to be loaded...
	# Awesome.
	def write_nodes(name, uri):
		"""Convenient func to add CSimpleNode entity"""
		ET.SubElement(model, "CSimpleNode",
		   name=name,
		   xloc="0.0", yloc="0.0"
		).text = \
			uri

	cadbiomNodes = set()
	for ori_ext_nodes, transitions in dictTransition.iteritems():

		# In transitions (ori/ext)
		cadbiomNodes.update(ori_ext_nodes)
		# In conditions
		cadbiomNodes.update(
			str(atom) for transition in transitions
			for atom in transition['sympyCond'].atoms()
		)

	# We want uri and cadbiom name for each entity in the model
	cadbiomNames = get_names_of_missing_physical_entities(dictPhysicalEntity)

	[write_nodes(cadbiomName, cadbiomNames[cadbiomName])
		for cadbiomName in cadbiomNodes]

	############################################################################
	# Anyway, next...
	# Get all transitions
	def write_transitions(ori_ext_nodes, event, condition, uris):
		"""Convenient func to add a transition"""
		left_entity, right_entity = ori_ext_nodes
		ET.SubElement(
			model, "transition",
			ori=left_entity, ext=right_entity,
			event=event,
			condition=condition,
			#action="", fact_ids="[]"
		).text = \
			uris

	for ori_ext_nodes, transitions in dictTransition.iteritems():

		if len(transitions) == 1:
			transition = transitions[0]
			write_transitions(
				ori_ext_nodes, transition["event"],
				formatCadbiomSympyCond(transition["sympyCond"]),
				"reaction=" + transition["reaction"],
			)

		else:
			events_conds = \
				{tuple((transition["event"], transition["sympyCond"]))
					for transition in transitions}

			# Get all uris of reactions involved in this transition
			uris = \
				','.join(transition['reaction'] for transition in transitions)

			write_transitions(
				ori_ext_nodes, formatEventAndCond(events_conds),
				"",
				"reaction=" + uris
			)

	tree = ET.ElementTree(model)
	tree.write(filePath, pretty_print=True)

	# Remove SCC (Strongly Connected Components) from the model
	mc.add_start_nodes(filePath)
