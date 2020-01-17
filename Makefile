install:
	@cd app && pipenv install --dev --system

unittest:
	@cd app && pipenv run unittest
