# DARTRIX OS Makefile

.PHONY: run replay clean test

run:
	python3 start_dartrix.py

replay:
	python3 replay.py

test:
	python3 -m unittest discover tests

clean:
	rm -f *.db
	rm -rf __pycache__
