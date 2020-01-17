install:
	@cd app && pipenv install --dev --system

lint:
	@cd app && pipenv run lint

unittest:
	@cd app && pipenv run unittest
