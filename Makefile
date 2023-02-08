clean:
	rm -rf __pycache__/
	rm -f lyrics.txt input

run:
	chmod +x ./autoytdlp.sh
	./autoytdlp.sh

conv:
	chmod +x ./convert.sh
	./convert.sh

tags:
	chmod +x ./id3tag.sh
	./id3tag.sh

pyformat:
	python3 -m autopep8 --in-place ./*.py

pycheck:
	python3 -m mypy ./*.py
	python3 -m pylint -j $(nproc) ./*.py
