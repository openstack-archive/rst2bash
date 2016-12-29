#!/usr/bin/env bash
set -o errexit -o nounset

# TODO: OUTPUT_DIR should either be read from the config file used by
#       parser.py or passed to parser.py (argument or environment variable);
#       every path should only be configured in one location
OUTPUT_DIR=build/scripts

mkdir -p "$OUTPUT_DIR"

REPO=openstack-manuals
# Only clone the repo if it does not exist yet. We could update an existing
# repo here, but skipping the repo instead allows for easy offline testing.
if [ ! -e build/$REPO ]; then
    git clone \
        --depth 10 \
        git://git.openstack.org/openstack/openstack-manuals \
        build/$REPO
fi

REPO=training-labs
if [ ! -e build/$REPO ]; then
    git clone \
        git://git.openstack.org/openstack/training-labs \
        build/$REPO
fi

# Aim at writing portable code that works with Python 2.x and (hopefully)
# with Python 3 as well.
python rst2bash/parser.py

echo "Output written to $OUTPUT_DIR"
