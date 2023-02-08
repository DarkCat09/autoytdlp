deps:
	python3 -m pip install -r requirements.txt

run:
	chmod +x ./autoytdlp.sh
	./autoytdlp.sh

conv:
	chmod +x ./convert.sh
	./convert.sh

tags:
	chmod +x ./id3tag.sh
	./id3tag.sh

clean:
	rm -rf __pycache__/
	rm -rf .mypy_cache/
	rm -f lyrics.txt input

rmfiles:
	rm -rf files/
	rm -rf convert/

pyformat:
	python3 -m autopep8 --in-place .*.py

pycheck:
	python3 -m mypy .*.py
	python3 -m pylint -j4 .*.py
