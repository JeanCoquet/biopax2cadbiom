# -*- coding: utf-8 -*-

# Standard imports
import argparse
import pytest

# Custom imports
import src.biopax2cadbiom as biopax2cadbiom
import src.commons as cm

LOGGER = cm.logger()


def args_to_param(args):
	"""Return argparse namespace as a dict {variable name: value}"""
	return {k: v for k, v in vars(args).items() if k != 'func'}


if __name__ == "__main__" :
	parser = argparse.ArgumentParser(
		description='biopax2cabiom.py is a script to transform a Biopax data \
		from a RDBMS to a Cabiom model.'
	)
	# Default log level: info
	parser.add_argument('-vv', '--verbose', nargs='?', default='info')

	parser.add_argument('--pickleBackup', type=str, nargs='?',
						default=cm.DIR_PICKLE + 'backup.p',
						help='output file path to save the script variables.'
	)
	parser.add_argument('--listOfGraphUri', nargs='+',
						help='list of RDF graph.'
	)
	parser.add_argument('--cadbiomFile', type=str, nargs='?',
						default=cm.DIR_OUTPUT + 'model.bcx',
						help='output file path to generate the Cadbiom model.'
	)
	parser.add_argument('--convertFullGraph', action='store_true',
						help='converts all entities to cadbiom nodes, '
							 'even the entities not used.'
	)
	parser.add_argument('--testCases', action='store_true',
						help='translates Biopax test cases to cadbiom models '
							 'and compares them with the cadbiom model '
							 'reference (if it exists).'
	)

	parser.set_defaults(func=biopax2cadbiom.main)

	# Get program args and launch associated command
	args = parser.parse_args()
	# Set log level
	cm.log_level(vars(args)['verbose'])
	# Take argparse arguments and put them in a standard dict
	params = args_to_param(args)

	if args.listOfGraphUri:
		args.func(params)

	if args.testCases:
		pytest.main(['./'])
