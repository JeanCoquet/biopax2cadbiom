# -*- coding: utf-8 -*-
# Standard imports
import argparse
import src.biopax2cadbiom as biopax2cadbiom
import src.testCases as testCases
from src.commons import DIR_PICKLE, DIR_OUTPUT, DIR_TEST_CASES


if __name__ == "__main__" :
	parser = argparse.ArgumentParser(
		description='biopax2cabiom.py is a script to transform a Biopax data \
		from a RDBMS to a Cabiom model.'
	)
	parser.add_argument('--pickleBackup', type=str, nargs='?',
						default=DIR_PICKLE + 'backup.p',
						help='enter a file path to save the script variables.'
	)
	parser.add_argument('--listOfGraphUri', nargs='+',
						help='enter a list of RDF graph.'
	)
	parser.add_argument('--cadbiomFile', type=str, nargs='?',
						default=DIR_OUTPUT + 'model.bcx',
						help='enter a file path to generate the Cadbiom model.'
	)
	parser.add_argument('--convertFullGraph', action='store_true',
						help='converts all entities to cadbiom nodes, even the entities not used.'
	)
	parser.add_argument('--testCases', action='store_true',
						help='translates Biopax test cases to cadbiom models and compares them with the cadbiom model reference (if it exists).'
	)
	parser.add_argument('--testCasesDir', type=str, nargs='?',
						default=DIR_TEST_CASES,
						help='Directory of test cases.'
	)
	
	parser.set_defaults(func=biopax2cadbiom.main)

	# get program args and launch associated command
	args = parser.parse_args()
	
	if args.listOfGraphUri:
		# Set log level
		#LOGGER.setLevel(cm.LOG_LEVELS[vars(args)['verbose']])
		# launch associated command
		args.func(args)
	
	if args.testCases:
		testCases.main(args)