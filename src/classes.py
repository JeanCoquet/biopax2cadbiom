class PhysicalEntity(object):
	"""
	Class for Physical Entity
		Attributes:
			name
			location
			entityType
			entityRef
		Optional
			synonym (set)
			component (set) 
			member (set)
			idRef (set)
			reactions (set)
			membersUsed(bool)
			cadbiomName (set)
	"""
	def __init__(self,idEntity,name,location,entityType,entityRef):
		self.idEntity = idEntity
		self.name = name
		self.location = location
		self.entityType = entityType
		self.entityRef = entityRef
		self.synonyms = set()
		self.components = set()
		self.members = set()
		self.idRefs = set()
		self.reactions = set()
		self.membersUsed = None
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
		return hash(self.idEntity)


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
			controllers(set)
			cadbiomSympyCond
			event
	"""

	def __init__(self,idReaction,name,reactiontype,productComponent,participantComponent):
		self.idReaction = idReaction
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
		return hash(self.idReaction)


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

	def __init__(self, idLocation,locationTerm):
		self.idLocation = idLocation
		self.name = locationTerm
		self.idRefs = set()
		self.cadbiomId = None

	def __hash__(self):
		"""Define object's unicity"""
		return hash(self.idLocation)


class Control(object):
	"""
	Class for Control:
		Attributes
			classType
			controlType
			reaction
			controller

	.. note: controlType is in (ACTIVATION, INHIBITION)
	"""
	def __init__(self,idControl,classType,controlType,reaction,controller):
		self.idControl = idControl
		self.classType = classType
		self.controlType = controlType
		self.reaction = reaction
		self.controller = controller

	@property
	def controlType(self):
		return self._controlType

	@controlType.setter
	def controlType(self, value):
		assert value in ('ACTIVATION', 'INHIBITION')
		self._controlType = value

	def __hash__(self):
		"""Define object's unicity"""
		return hash(self.idControl)
