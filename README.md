Convert Biopax data (http://biopax.org) to Cabiom model (http://cadbiom.genouest.org).


## Help

	$ python -m src -h
	usage: __main__.py [-h] [--pickleBackup [PICKLEBACKUP]]
					[--listOfGraphUri LISTOFGRAPHURI [LISTOFGRAPHURI ...]]
					[--cadbiomFile [CADBIOMFILE]]

	biopax2cabiom.py is a script to transforme a Biopax data from a RDBMS to a
	Cabiom model.

	optional arguments:
	-h, --help            show this help message and exit
	--pickleBackup [PICKLEBACKUP]
							enter a file path to save the script variables.
	--listOfGraphUri LISTOFGRAPHURI [LISTOFGRAPHURI ...]
							enter a list of RDF graph.
	--cadbiomFile [CADBIOMFILE]
							enter a file path to generate the Cadbiom model.


## Example of command line :

	python3 -m src --listOfGraphUri http://biopax.org/lvl3 http://www.pathwaycommons.org/reactome_v56

<br>
or

	python3 -m src --pickleBackup backupPickle/backup.p --cadbiomFile output/tgfBetaTestModel.bcx --listOfGraphUri http://biopax.org/lvl3 http://www.pathwaycommons.org/tgfbrpathway
