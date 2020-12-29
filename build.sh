#!/bin/bash

# '''
# Example:
#  ./build.sh -DBUILD_KVS=ON
# '''

full_path=$(realpath $0)
dir_path=$(dirname $full_path)/

rm -rf ~/.cache/gstreamer-1.0/

cd $dir_path

    if [ ! -d build ]; then
        mkdir build
    fi

    if [ -d build ]; then
        cd build
            cmake .. $@
            make
        cd ..
    fi

cd ..
