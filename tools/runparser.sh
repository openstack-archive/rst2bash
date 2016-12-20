#!/bin/bash -

mkdir -p build/scripts
git clone \
    --depth 10 \
    git://git.openstack.org/openstack/openstack-manuals \
    build/openstack-manuals
git clone \
    git://git.openstack.org/openstack/training-labs \
    build/training-labs

python2.7 rst2bash/parser.py

echo "Please find the generated BASH scripts in the build/scripts folder!".
