# -*- coding: utf-8 -*-

# Standard imports
import argparse
import pytest

# Custom imports
import src.biopax2cadbiom as biopax2cadbiom
import src.commons as cm

LOGGER = cm.logger()


def run_tests(args):
	"""Translates BioPAX test cases to cadbiom models and compares
	them with the cadbiom model reference (if it exists).
	"""

	pytest.main(['./'])


def make_model(args):
	"""Make CADBIOM model with BioPAX data obtained from a triplestore."""

	# Take argparse arguments and put them in a standard dict
	params = args_to_param(args)
	biopax2cadbiom.main(params)


def args_to_param(args):
	"""Return argparse namespace as a dict {variable name: value}"""
	return {k: v for k, v in vars(args).items() if k != 'func'}


if __name__ == "__main__" :

	parser = argparse.ArgumentParser(
		description="biopax2cabiom is a script to transform a BioPAX RDF data \
		from a triplestore to a CADBIOM model.",
	)
	# Default log level: info
	parser.add_argument('-vv', '--verbose', nargs='?', default='info')
	# Subparsers
	subparsers = parser.add_subparsers(title='subcommands')

	# subparser: Tests
	# Just write the parameter 'tests'
	parser_run_tests = subparsers.add_parser('tests', help=run_tests.__doc__)
	parser_run_tests.set_defaults(func=run_tests)


	# subparser: Make model
	#
	parser_make_model = subparsers.add_parser('model',
		help=make_model.__doc__,
		formatter_class=argparse.ArgumentDefaultsHelpFormatter
	)
	# Pickle backup of queries
	parser_make_model.add_argument('--pickleBackup', action='store_true',
		help="Allows to save/reuse the results of SPARQL queries."
			 "The goal is to save querying time during tests with same inputs."
	)
	parser_make_model.add_argument('--pickleDir', type=str, nargs='?',
		default=cm.DIR_PICKLE + 'backup.p',
		help="Output file path to save the script variables."
	)

	# Triplestore settings
	parser_make_model.add_argument('--listOfGraphUri', nargs='+',
		help="List of RDF graph to be queried on the triplestore."
	)
	parser_make_model.add_argument('--triplestore', type=str, nargs='?',
		default=cm.SPARQL_PATH,
		help="URL of the triplestore."
	)

	# Model options
	parser_make_model.add_argument('--cadbiomFile', type=str, nargs='?',
		default=cm.DIR_OUTPUT + 'model.bcx',
		help="Output file path to generate the Cadbiom model."
			 "2 models are created: A basic model and a model without strongly "
			 "connected components that block CADBIOM solver."
	)
	parser_make_model.add_argument('--convertFullGraph', action='store_true',
		help="Converts all entities to cadbiom nodes, "
			 "even the entities not used."
	)
	parser_make_model.add_argument('--fullCompartmentsNames', action='store_true',
		help="If set, compartments will be encoded on the base "
			 "of their real names instead of numeric values."
	)
	parser_make_model.add_argument('--blacklist', type=str, nargs='?',
		help="If set, the entities in the given file will be"
			 "banished from conditions of transitions "
			 " (ex: cofactors or entities of energy metabolism)"
	)

	parser_make_model.set_defaults(func=make_model)

	# Get program args and launch associated command
	args = parser.parse_args()

	# Set log level
	cm.log_level(vars(args)['verbose'])

	# Launch associated command
	args.func(args)
