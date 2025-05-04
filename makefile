all: build upload

build:
	py -m build

upload:
	py -m twine upload dist/*
