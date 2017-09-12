all: clean sdist

clean:
	@echo Clean Python build dir...
	python2.7 setup.py clean --all
	@echo Clean Python distribution dir...
	@-rm -rf dist
	@-rm -rf *egg-info

sdist:
	@echo Building the distribution package...
	python2.7 setup.py sdist

install:
	@echo Install the package...
	python2.7 setup.py install --record files.txt

uninstall: files.txt
	@echo Uninstalling the package...
	cat files.txt | xargs rm -rf
	rm files.txt

dev_install:
	@echo Install the package for developers...
	python2.7 setup.py develop

dev_uninstall:
	@echo Uninstalling the package for developers...
	python2.7 setup.py develop --uninstall

unit_tests:
	@echo Launch unit tests
	python2.7 setup.py test

upload: clean sdist
	python setup.py bdist_wheel
	twine upload dist/* -r pypitest_inria

t:
	pytest

p:
	python -m biopax2cadbiom model --listOfGraphUri http://biopax.org/lvl3 http://www.pathwaycommons.org/v9/pid --fullCompartmentsNames

m:
	python -m biopax2cadbiom model --listOfGraphUri http://biopax.org/lvl3 http://reactome.org/mycobacterium --fullCompartmentsNames --convertFullGraph
	cadbiom_cmd model_comp testCases/refs/mycobacterium.bcx output/model.bcx --json --graphs

i:
	cadbiom_cmd model_infos output/model.bcx --graph --json
