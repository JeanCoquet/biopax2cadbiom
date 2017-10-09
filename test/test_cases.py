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

"""
This module is used to translate Biopax test cases to cadbiom models
and compare them with the cadbiom model reference (if it exists).

.. note:: To add a test, please add it to test_pool dictionnary.
	key: name of the test,
	value: tuple of a list of uris and path to a potential blacklist file.

"""

from __future__ import unicode_literals
from __future__ import print_function

# Standard imports
import os
from functools import partial
import pytest

# Custom imports
import biopax2cadbiom.biopax_converter as b2c
from biopax2cadbiom.commons import DIR_TEST_CASES, DIR_LOGS, SPARQL_PATH
from cadbiom_cmd.solution_repr import graph_isomorph_test

# Tests and params
# tuple: 0: list of uris, 1: blacklist_file, 2: convertFullGraph
test_pool = {
		'homarus': (['http://biopax.org/lvl3', 'http://reactome.org/homarus'], None, True),
		'crithidia': (['http://biopax.org/lvl3', 'http://reactome.org/crithidia'], None, True),
		'vigna': (['http://biopax.org/lvl3', 'http://reactome.org/vigna'], None, True),
		'triticum': (['http://biopax.org/lvl3', 'http://reactome.org/triticum'], None, True),
		'cavia': (['http://biopax.org/lvl3', 'http://reactome.org/cavia'], None, True),
		'escherichia': (['http://biopax.org/lvl3', 'http://reactome.org/escherichia'], None, True),
		'cricetulus': (['http://biopax.org/lvl3', 'http://reactome.org/cricetulus'], None, True),
		'cricetulusWithoutSmallMolecules': (['http://biopax.org/lvl3', 'http://reactome.org/cricetulus'], DIR_TEST_CASES + 'blacklists/cricetulusSmallMolecules.csv', True),
		'mycobacterium': (['http://biopax.org/lvl3', 'http://reactome.org/mycobacterium'], None, True),
		'virtualCase1': (['http://biopax.org/lvl3', 'http://virtualcases.org/1'], None, True),
		'virtualCase2': (['http://biopax.org/lvl3', 'http://virtualcases.org/2'], None, True),
		'virtualCase3': (['http://biopax.org/lvl3', 'http://virtualcases.org/3'], None, False),
		'virtualCase4': (['http://biopax.org/lvl3', 'http://virtualcases.org/4'], None, False),
		'virtualCase5': (['http://biopax.org/lvl3', 'http://virtualcases.org/5'], None, True),
	}


def t_model(model_name, uris, blacklist_file, convertFullGraph):
	"""Build model & check it vs a reference model.

	.. note:: convertFullGraph = True: We decompose entities in classes even
		if they are not involved elsewhere.
	"""

	# Build parameters for biopax2cadbiom
	params = {
		'cadbiomFile': DIR_LOGS + 'model.bcx',
		'convertFullGraph': convertFullGraph,
		'listOfGraphUri': uris,
		'pickleBackup': False,
		'pickleDir': DIR_LOGS + 'backup.p', # osef, pickleBackup = False
		'fullCompartmentsNames': True,
		'blacklist': blacklist_file,
		'triplestore': SPARQL_PATH,
		'no_scc_fix': False, # Change this if you don't want SCC fix
	}

	b2c.main(params)

	# Build files path
	found_model = params['cadbiomFile']
	ref_model = DIR_TEST_CASES + 'refs/' + model_name + '.bcx'

	# Run isomorphic test between the 2 models (constructed and reference)
	check_state = \
		graph_isomorph_test(
			found_model,
			ref_model,
		)

	# Check if tests are ok
	for test, found_state in check_state.iteritems():
		test_message = "{} test failed for '{}' !".format(
			test.title(),
			model_name,
		)
		assert found_state == True, test_message


def clean_test_env(dir):
	"""Try to remove previous model & pickle file if they exist."""

	try:
		os.remove(dir + 'model.bcx')
	except OSError:
		pass

	try:
		os.remove(dir + 'backup.p')
	except OSError:
		pass


@pytest.yield_fixture(autouse=True)
def fixture_me():
	"""Fixture that is launched before and after all tests.

	.. note:: autouse allows to launch the fixture without explicitly noting it.
	"""

	clean_test_env(DIR_TEST_CASES)


for specie, params in test_pool.iteritems():
	"""Create test functions based on test_pool variable."""
	func = partial(t_model,
				   model_name=specie, uris=params[0], blacklist_file=params[1], convertFullGraph=params[2])
	globals()['test_' + specie] = func
