#!/bin/bash

P=`dirname $0`


for i in "$@"; do
    B=`basename $i`
    D=`dirname $i`
    BWE=`basename $i .log`

    $P/log2csv.py -x $BWE $i -o "$D/$BWE-raw.csv" && $P/import.py -a time_ns "$D/$BWE-raw.csv" -o "$D/$BWE.csv"
done;
