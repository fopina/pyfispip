pub:
	python setup.py sdist upload

pubtest:
	python setup.py sdist upload -r https://testpypi.python.org/pypi

pip:
	docker create --privileged --name fispipdev -p 61315:61315 fopina/fis-pip

runpip:
	docker start fispipdev

test:
	nosetests