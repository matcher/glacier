#!/bin/bash

path=`pwd`
path=`dirname $path`
path=`dirname $path`

cmd="cimri/module/automation/controller.py --host localhost --port 10000"

echo $path

export PYTHONPATH="$path"
`python $cmd`
