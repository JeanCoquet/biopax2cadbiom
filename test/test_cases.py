# -*- coding: utf-8 -*-
"""
This module is used to translate Biopax test cases to cadbiom models
and compare them with the cadbiom model reference (if it exists).

Tests:

'homarus': ['http://biopax.org/lvl3', 'http://reactome.org/homarus'],
'crithidia': ['http://biopax.org/lvl3', 'http://reactome.org/crithidia'],
'vigna': ['http://biopax.org/lvl3', 'http://reactome.org/vigna'],
'triticum': ['http://biopax.org/lvl3', 'http://reactome.org/triticum'],
'cavia': ['http://biopax.org/lvl3', 'http://reactome.org/cavia'],
'virtualCase1': ['http://biopax.org/lvl3', 'http://virtualcases.org/1'],
'virtualCase2': ['http://biopax.org/lvl3', 'http://virtualcases.org/2'],
'escherichia': ['http://biopax.org/lvl3', 'http://reactome.org/escherichia'],
'cricetulus': ['http://biopax.org/lvl3', 'http://reactome.org/cricetulus'],
'mycobacterium': ['http://biopax.org/lvl3', 'http://reactome.org/mycobacterium']
"""

from __future__ import unicode_literals
from __future__ import print_function

# Standard imports
import os

# Custom imports
import src.biopax2cadbiom as biopax2cadbiom
from src.commons import DIR_TEST_CASES
#from src.commons import FILE_README
from cadbiom_cmd.solution_repr import graph_isomorph_test


def test_1():
	t_model({'homarus': ['http://biopax.org/lvl3', 'http://reactome.org/homarus']})

def test_2():
	t_model({'crithidia': ['http://biopax.org/lvl3', 'http://reactome.org/crithidia']})

def test_3():
	t_model({'vigna': ['http://biopax.org/lvl3', 'http://reactome.org/vigna']})

def test_4():
	t_model({'triticum': ['http://biopax.org/lvl3', 'http://reactome.org/triticum']})

def test_5():
	t_model({'cavia': ['http://biopax.org/lvl3', 'http://reactome.org/cavia']})

def test_6():
	t_model({'escherichia': ['http://biopax.org/lvl3', 'http://reactome.org/escherichia']})

def test_7():
	t_model({'cricetulus': ['http://biopax.org/lvl3', 'http://reactome.org/cricetulus']})

def test_8():
	t_model({'mycobacterium': ['http://biopax.org/lvl3', 'http://reactome.org/mycobacterium']})

def test_9():
	t_model({'virtualCase1': ['http://biopax.org/lvl3', 'http://virtualcases.org/1']})

def test_10():
	t_model({'virtualCase2': ['http://biopax.org/lvl3', 'http://virtualcases.org/2']})


def t_model(feed_statement):
	"""Build model & check it vs a reference model.

	.. note:: convertFullGraph = True: We decompose entities in classes even
		if they are not involved elsewhere.
	"""

	clean_test_env(DIR_TEST_CASES)

	for model_name, uris in feed_statement.iteritems():

		# Build parameters for biopax2cadbiom
		params = {
			'cadbiomFile': DIR_TEST_CASES + 'model.bcx',
			'convertFullGraph': True,
			'listOfGraphUri': uris,
			'pickleBackup': DIR_TEST_CASES + 'backup.p',
			'testCasesDir': DIR_TEST_CASES,
			'fullCompartmentsNames': True,
			'blacklist': False,
		}

		biopax2cadbiom.main(params)

		# Build files path
		found_model = params['cadbiomFile']
		ref_model = DIR_TEST_CASES + 'refs/' + model_name + '.bcx'

		# Run isomorphic test between the 2 models (constructed and reference)
		check_state = \
			graph_isomorph_test(
				found_model,
				ref_model,
				output_dir=DIR_TEST_CASES,
			)

		# Check if tests are ok
		for test, found_state in check_state.iteritems():
			test_message = "{} test failed for '{}' !".format(
				test.title(),
				model_name,
			)
			assert found_state == True, test_message

		clean_test_env(DIR_TEST_CASES)


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
