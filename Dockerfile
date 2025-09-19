FROM python:3.12-slim

RUN apt-get update

##  MAKE DATA DIRECTORIES
RUN mkdir -p /data/outputs/
RUN mkdir -p /data/inputs/







##  MOVE PYTHON FILES TO CONTAINER ROOT (`dafni_entrypoint.py` & `setup.py`)
COPY *.py ./

##  MOVE DRES LIBRARY TO CONTAINER ROOT
RUN mkdir -p /dres/
COPY dres/*.py ./dres/

##  INSTALL ALL PYTHON DEPENDENCIES USING `setup.py` (PIP INSTALL)
RUN pip install .

##  RUN MODEL
CMD python dafni_entrypoint.py