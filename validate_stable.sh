#!/bin/bash

set -e
rm -f dummy*
./gen_metadata.py dummy
./gen_metadata.py binparse dummy.bin -j dummy2.json
./gen_metadata.py jsonparse dummy2.json -b dummy2.bin
shasum dummy*.bin
