#!/bin/bash
# Generate the binary release, i.e. a .zip file.

# Switch to repo root dir
MYDIR=`dirname $0`
pushd ${MYDIR} >/dev/null

# Prepare
TAG=`git tag -l|sort -V|head -n 1`
WORKDIR=`mktemp -d`
PACKAGE=weewx-mqtt-input
STAGE=${WORKDIR}/${PACKAGE}

# Create staging area
mkdir -p ${STAGE}
cp -r bin ${STAGE}
cp README.md ${STAGE}
cp LICENSE ${STAGE}
cp install.py ${STAGE}

# Create archices
pushd ${WORKDIR} >/dev/null
tar cvzf ${PACKAGE}-$TAG.tar.gz ${PACKAGE}
7z a ${PACKAGE}-${TAG}.zip ${PACKAGE}
popd >/dev/null

# Cleanup
mv ${WORKDIR}/*tar.gz .
mv ${WORKDIR}/*zip .
popd >/dev/null
rm -rf ${WORKDIR}
