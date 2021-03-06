#!/bin/sh

python setup.py build_ext --fcompiler=gnu95 build

unset PYTHONPATH
BUILD_DIR=$(find $PWD/build -mindepth 1 -name "lib.*" -type d)
export PYTHONPATH=$BUILD_DIR:$PYTHONPATH
pdoc --html --html-no-source --overwrite --html-dir 'docs' pytdlpack
pdoc --html --html-no-source --overwrite --html-dir 'docs' TdlpackIO
