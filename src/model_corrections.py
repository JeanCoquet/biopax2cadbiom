# -*- coding: utf-8 -*-
"""
This module is used to bring some corrections to Cadbiom model processed before.

	- Removing of Strongly Connected Components
	(cycles of disabled places that can never be activated by the solver)

"""
from __future__ import unicode_literals
from __future__ import print_function

# Standard imports
import os

# Custom imports
from cadbiom.models.guard_transitions.analyser.static_analysis \
	import StaticAnalyzer
from cadbiom.models.guard_transitions.translators.chart_xml \
	import XmlVisitor
import src.commons as cm

LOGGER = cm.logger()


class ErrorRep(object):
	# Cf class CompilReporter(object):
	# gt_gui/utils/reporter.py
	def __init__(self):
		self.context = ""
		self.error = False

	def display(self, mess):
		self.error = True
		LOGGER.error(">> Context: {}; {}".format(self.context, mess))
		exit()

	def display_info(self, mess):
		LOGGER.error("-- Context: {}; {}".format(self.context, mess))
		exit()

	def set_context(self, cont):
		self.context = cont


def add_start_nodes(filePath):
	"""Handle Strongly Connected Components (SCC) by adding Start Nodes

	.. note:: Only 1 start node in each SCC is sufficient to suppress it
		from the model.
	.. note:: We use cadbiom API to add Start Nodes and write a new model.

	:param: File path.
	:type: <str>
	"""

	# Build StaticAnalyzer with Error Reporter
	staticanalyser = StaticAnalyzer(ErrorRep())
	staticanalyser.build_from_chart_file(filePath)
	# Get Strongly Connected Components
	sccs = staticanalyser.get_frontier_scc()

	LOGGER.info("{} SCC found: {}".format(len(sccs), sccs))
	LOGGER.info("Before adding start nodes: " + staticanalyser.get_statistics())

	# Lexicographic sort of nodes in each Strongly Connected Components
	g = (scc for scc in sccs if len(scc) != 0)
	for scc in g:
		scc.sort(key=str.lower)
		# Mark the first node as a frontier
		LOGGER.debug("SCC {}; first lexicographic node:{}".format(scc, scc[0]))
		staticanalyser.model.mark_as_frontier(scc[0])

	# Save the model with "_without_scc" suffix in filename
	xml = XmlVisitor(staticanalyser.model)
	filename, file_extension = os.path.splitext(filePath)
	mfile = open(filename + "_without_scc" + file_extension, 'w')
	mfile.write(xml.return_xml())
	mfile.close()
