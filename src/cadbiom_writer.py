# -*- coding: utf-8 -*-
"""
This module is used export biopax processed data to cabiom model file format.
"""

# Standard imports
import sympy
from lxml import etree as ET
from collections import defaultdict


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
	# remove and return an arbitrary element from s; raises KeyError if empty ?????????????????????
	event, cond = setOfEventAndCond.pop()
	s = "("+event+") when ("+formatCadbiomSympyCond(cond)+")"
	if len(setOfEventAndCond) == 0:
		return s
	else:
		return "("+s+") default ("+formatEventAndCond(setOfEventAndCond)+")"


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
	model = ET.Element("model", xmlns="http://cadbiom", name=nameModel)

	# Get all nodes
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
	# Get all names and their uris
	cadbiomNames = defaultdict(lambda: "")
	for entity in dictPhysicalEntity.values():
		cadbiomNames[entity.cadbiomName] = entity.uri
		for cadbiomNameWithMembers in entity.listOfCadbiomNames:
			cadbiomNames[cadbiomNameWithMembers] = entity.uri

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
