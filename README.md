# biopax2cadbiom

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


## Example of command line

	python3 -m src --listOfGraphUri http://biopax.org/lvl3 http://www.pathwaycommons.org/reactome_v56

## Test cases

### Reactome - Homarus_americanus.owl
__Command__: `python3 -m src --listOfGraphUri http://biopax.org/lvl3 http://reactome.org/homarus`
  * [x] Expected result
  * [x] No errors
  * [x] No unexpected transitions

![ImageOfHomarusTestCase](img/testCases/homarus.png)

<br/>

### Reactome - Crithidia_fasciculata.owl
__Command__: `python3 -m src --listOfGraphUri http://biopax.org/lvl3 http://reactome.org/crithidia`
  * [x] Expected result
  * [x] No errors
  * [x] No unexpected transitions

![ImageOfCrithidiaTestCase](img/testCases/crithidia.png)

<br/>

### Reactome - Vigna_radiata_var._radiata.owl
__Command__: `python3 -m src --listOfGraphUri http://biopax.org/lvl3 http://reactome.org/vigna`
  * [x] Expected result
  * [x] No errors
  * [x] No unexpected transitions

![ImageOfVignaTestCase](img/testCases/vigna.png)

<br/>

### Reactome - Triticum_aestivum.owl
__Command__: `python3 -m src --listOfGraphUri http://biopax.org/lvl3 http://reactome.org/triticum`
  * [x] Expected result
  * [x] No errors
  * [x] No unexpected transitions

![ImageOfTriticumTestCase](img/testCases/triticum.png)

<br/>

### Reactome - Cavia_porcellus.owl
__Command__: `python3 -m src --listOfGraphUri http://biopax.org/lvl3 http://reactome.org/cavia`
  * [ ] Expected result
  * [x] No errors
  * [x] No unexpected transitions

__Comments__:
  * A transition without condition must be empty (there is a 'True')
  * How to process the 'members' in this case?

![ImageOfCaviaTestCase](img/testCases/cavia.png)

