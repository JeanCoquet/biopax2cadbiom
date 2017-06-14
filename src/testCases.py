# -*- coding: utf-8 -*-
"""
This module is used to translate Biopax test cases to cadbiom models and compare them with the cadbiom model reference (if it exists).
"""

import os, sys
import src.biopax2cadbiom as biopax2cadbiom
from src.commons import FILE_README
from cadbiom_cmd.solution_repr import graph_isomorph_test

def runBiopaxToCadbiom(args, nameTestCase, testCasesDir, graphUri):
	args.listOfGraphUri = ['http://biopax.org/lvl3', graphUri]
	args.cadbiomFile = testCasesDir+'model.bcx'
	args.convertFullGraph = True
	args.pickleBackup = testCasesDir+'backup.p'
	
	currentStderr = sys.stderr
	
	sys.stderr = open(testCasesDir+'stderr.txt', 'w')
	biopax2cadbiom.main(args)
	sys.stderr = currentStderr
	
	errors, unexpectedReactions = havingErrors(testCasesDir+'stderr.txt')
	
	if not errors:
		expectedResult = compareModelToRef(testCasesDir+'model.bcx', testCasesDir+'refs/'+nameTestCase+'.bcx')
	else:
		expectedResult = False
	
	os.remove(testCasesDir+'stderr.txt')
	os.remove(testCasesDir+'model.bcx')
	os.remove(testCasesDir+'backup.p')
	
	return expectedResult, errors, unexpectedReactions

def havingErrors(stderrPath):
	errors, unexpectedReactions = False, False
	with open(stderrPath) as stderrFile:
		for line in stderrFile:
			if line[:10] == 'UNEXCEPTED REACTION':
				unexpectedReactions = True
			else:
				errors = True
	return errors, unexpectedReactions


def compareModelToRef(modelPath, refPath):
	check_state = graph_isomorph_test(modelPath, refPath, "")
	return check_state['topology'] and check_state['nodes'] and check_state['edges']


def printTestCase(dictTestCase):
	print(dictTestCase['source']+' - '+dictTestCase['owlFile'])
	print('Command: python3 -m src --convertFullGraph --listOfGraphUri http://biopax.org/lvl3 '+dictTestCase['graphUri'])
	if dictTestCase['expectedResult']: print('\t'+'[x] Expected result')
	else: print('\t'+'[ ] Expected result')
	if not dictTestCase['errors']: print('\t'+'[x] No errors')
	else: print('\t'+'[ ] No errors')
	if not dictTestCase['unexpectedReactions']: print('\t'+'[x] No unexpected reactions')
	else: print('\t'+'[ ] No unexpected reactions')
	print("")


def updateReadme(listOfDictTestCase, readmePath, testCasesDir):
	with open(readmePath) as readmeFile:
		readmeLines = readmeFile.readlines()
	
	with open(readmePath+'2', 'w') as readmeFile:
		numLine = 0
		while readmeLines[numLine] != '[//]: # (TESTS_START)\n':
			readmeFile.write(readmeLines[numLine])
			numLine += 1
		readmeFile.write('[//]: # (TESTS_START)\n')
		
		for i in range(len(listOfDictTestCase)):
			dictTestCase = listOfDictTestCase[i]
			
			if dictTestCase['expectedResult'] and not dictTestCase['errors'] and not dictTestCase['unexpectedReactions']:
				readmeFile.write('### {+ '+dictTestCase['source']+' - '+dictTestCase['owlFile']+' +}\n')
			else:
				readmeFile.write('### {- '+dictTestCase['source']+' - '+dictTestCase['owlFile']+' -}\n')
			
			readmeFile.write('__Command__: `python -m src --convertFullGraph --listOfGraphUri http://biopax.org/lvl3 '+dictTestCase['graphUri']+'`\n')
			
			if dictTestCase['expectedResult']: readmeFile.write('  * [x] Expected result\n')
			else: readmeFile.write('  * [ ] Expected result\n')
			if not dictTestCase['errors']: readmeFile.write('  * [x] No errors\n')
			else: readmeFile.write('  * [ ] No errors\n')
			if not dictTestCase['unexpectedReactions']: readmeFile.write('  * [x] No unexpected reactions\n')
			else: readmeFile.write('  * [ ] No unexpected reactions\n')
			readmeFile.write('\n')
			
			if os.path.isfile(testCasesDir+'img/'+dictTestCase['name']+'.png'):
				readmeFile.write('![Image_'+dictTestCase['name']+']('+testCasesDir+'img/'+dictTestCase['name']+'.png)\n\n')
			
			if i < len(listOfDictTestCase)-1:
				readmeFile.write('<br/>\n\n')
		
		while readmeLines[numLine] != '[//]: # (TESTS_END)\n':
			numLine += 1
		
		for line in readmeLines[numLine:]:
			readmeFile.write(line)

def main(args):
	
	testCasesDir = args.testCasesDir
	if testCasesDir[-1] != '/': 
		testCasesDir=+'/'
	
	listOfDictTestCase = []
	
	if os.path.isfile(testCasesDir+'listOfGraphUri.txt'):
		with open(testCasesDir+'listOfGraphUri.txt') as listOfGraphUriFile:
			for line in listOfGraphUriFile:
				nameTestCase, source, owlFile, graphUri = line[:-1].split('\t',4)
				expectedResult, errors, unexpectedReactions = runBiopaxToCadbiom(args, nameTestCase, testCasesDir, graphUri)
				
				dictTestCase = {}
				dictTestCase['name'] = nameTestCase
				dictTestCase['source'] = source
				dictTestCase['owlFile'] = owlFile
				dictTestCase['graphUri'] = graphUri
				dictTestCase['expectedResult'] = expectedResult
				dictTestCase['errors'] = errors
				dictTestCase['unexpectedReactions'] = unexpectedReactions
				listOfDictTestCase.append(dictTestCase)
				
				printTestCase(dictTestCase)
		
	#updateReadme(listOfDictTestCase, FILE_README, testCasesDir)
	