#!/bin/bash

VERBOSE=0
SEPARATOR="\033[94m--------------------------------------------------------------------------\033[0m"
if [ $VERBOSE -eq 1 ]; then
	set -eux
	OPTS=-v
else
	set -e
	OPTS=
fi

rm -f dummy.bin dummy.json a.bin a.json

./gen_metadata.py dummy $OPTS
echo -e "$SEPARATOR"
./gen_metadata.py jsonparse $OPTS dummy.json -b a.bin
echo -e "$SEPARATOR"
./gen_metadata.py binparse $OPTS dummy.bin -j a.json
echo -e "$SEPARATOR"
./gen_metadata.py shell $OPTS -b a.bin -j a.json -- set_bank_policy img_0 0 refuse, dump
echo -e "$SEPARATOR"
./gen_metadata.py shell $OPTS -b a.bin -j a.json -- print_all_uuids
echo -e "$SEPARATOR"
./gen_metadata.py shell $OPTS -b a.bin -j a.json -- print_choices_uuids, set_active_index 0, print_choices_uuids
echo -e "$SEPARATOR"
./gen_metadata.py shell $OPTS -b a.bin -j a.json -- set_bank_policy img_0 0 accept, print_choices_uuids
echo -e "$SEPARATOR"
./gen_metadata.py test $OPTS
