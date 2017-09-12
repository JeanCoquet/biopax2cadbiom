# -*- coding: utf-8 -*-
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

"""Entry point and argument parser for cadbiom2biopax"""

# Standard imports
import argparse
import pytest
import pkg_resources

# Custom imports
import biopax2cadbiom.biopax_converter as b2c
import biopax2cadbiom.commons as cm

LOGGER = cm.logger()


def run_tests(dummy_args):
	"""Translates BioPAX test cases to cadbiom models and compares
	them with the cadbiom model reference (if it exists).
	"""

	# Run pytest on the current package directory (where 'test' dir is)
	package_dir = pkg_resources.resource_filename(
		__name__,
		'../'
	)

	pytest.main([package_dir])
	exit()


def make_model(args):
	"""Make CADBIOM model with BioPAX data obtained from a triplestore."""

	# Take argparse arguments and put them in a standard dict
	params = args_to_param(args)
	b2c.main(params)


def args_to_param(args):
	"""Return argparse namespace as a dict {variable name: value}"""
	return {k: v for k, v in vars(args).items() if k != 'func'}


def main():
	"""Entry point"""

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
	parser_make_model = subparsers.add_parser('model',\
		help=make_model.__doc__,\
		formatter_class=argparse.ArgumentDefaultsHelpFormatter\
	)
	# Triplestore settings
	parser_make_model.add_argument('--listOfGraphUri', nargs='+', required=True,
		help="List of RDF graph to be queried on the triplestore."
	)
	parser_make_model.add_argument('--triplestore', type=str, nargs='?',
		default=cm.SPARQL_PATH,
		help="URL of the triplestore."
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
