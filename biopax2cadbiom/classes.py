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

"""This modules describes classes on top of BioPAX formalism."""

class PhysicalEntity(object):
	"""
	Class for Physical Entity
		Attributes:
			name
			location
			entityType
			entityRef (str) (not a set!)
		Optional
			synonym (set)
			components (set)
			members (set)
			idRefs (set)
			reactions (set)
			membersUsed (set)
			cadbiomName (set)
			listOfFlatComponents (list)
			listOfCadbiomNames (list)
	"""
	def __init__(self,uri,name,location,entityType,entityRef):
		self.uri = uri
		self.name = name
		self.location = location
		self.entityType = entityType
		self.entityRef = entityRef
		self.synonyms = set()
		self.components = set()
		self.members = set()
		self.idRefs = set()
		self.reactions = set()
		self.membersUsed = set()
		self.cadbiomName = set()
		self.listOfFlatComponents = []
		self.listOfCadbiomNames = []

	@property
	def entityType(self):
		return self._entityType

	@entityType.setter
	def entityType(self, value):
		self._entityType = value.rsplit("#", 1)[1]

	def __hash__(self):
		"""Define object's unicity"""
		return hash(self.uri)

	def __repr__(self):
		return "\n".join(
			attr + ':' + str(val) for attr, val in self.__dict__.iteritems()
		)


class Reaction(object):
	"""
	Class for reaction:
		Attributes:
			name
			reactiontype
			productcomponent
			participantcomponent
		Optional
			pathways (set)
			leftcomponents
			rightcomponents
			controllers (set)   => entities that control the reaction
			cadbiomSympyCond
			event
	"""

	def __init__(self,uri,name,reactiontype,productComponent,participantComponent):
		self.uri = uri
		self.name = name
		self.reactiontype = reactiontype
		self.productComponent = productComponent
		self.participantComponent = participantComponent
		self.pathways = set()
		self.leftComponents = set()
		self.rightComponents = set()
		self.controllers = set()
		self.cadbiomSympyCond = None
		self.event = None

	@property
	def reactiontype(self):
		return self._reactiontype

	@reactiontype.setter
	def reactiontype(self, value):
		self._reactiontype = value.rsplit("#", 1)[1]

	def __hash__(self):
		"""Define object's unicity"""
		return hash(self.uri)


class Location(object):
	"""
	Class for Location:
		Attributes
			locationTerm
			dbRef
		Optional
			idRef
			cadbiomId
	"""

	def __init__(self, uri,locationTerm):
		self.uri = uri
		self.name = locationTerm
		self.idRefs = set()
		self.cadbiomId = None

	def __hash__(self):
		"""Define object's unicity"""
		return hash(self.uri)


class Control(object):
	"""
	Class for Control:
		Attributes
			classType
			controlType => type of control (ACTIVATION or INHIBITION)
			reaction	=> reaction controlled
			controller  => entity that controls the reaction
			evidences   => set of evidences uris (identify controllers of the
						same reaction)

	.. note: controlType is in (ACTIVATION, INHIBITION)
	"""
	def __init__(self,idControl,classType,controlType,reaction,controller):
		self.uri = idControl
		self.classType = classType
		self.controlType = controlType
		self.reaction = reaction
		self.controller = controller
		self.evidences = set()

	@property
	def controlType(self):
		return self._controlType

	@controlType.setter
	def controlType(self, value):
		assert value in ('ACTIVATION', 'INHIBITION')
		self._controlType = value

	def __hash__(self):
		"""Define object's unicity"""
		return hash(self.uri)
