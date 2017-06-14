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

class Control(object):
	"""
	Class for Control:
		Attributes
			classType
			controlType
			reaction
			controller
	"""
	def __init__(self,idControl,classType,controlType,reaction,controller):
		self.idControl = idControl
		self.classType = classType
		self.controlType = controlType
		self.reaction = reaction
		self.controller = controller
