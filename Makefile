dist-mac:
	pdm run dist-mac

dist-win:
	pdm run dist-win

check:
	ruff check src

format:
	ruff format src

.PHONY: dist-mac dist-win check format
