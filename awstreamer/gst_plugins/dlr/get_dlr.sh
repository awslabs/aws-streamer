#!/bin/bash

if [ ! -d neo-ai-dlr ]; then
    git clone --recursive https://github.com/neo-ai/neo-ai-dlr --depth 1
fi

if [ ! -d neo-ai-dlr/build ]; then
    # source venv/bin/activate
    cd neo-ai-dlr
        mkdir build
        cd build
            # cmake .. -DUSE_CUDA=ON -DUSE_CUDNN=ON -DUSE_TENSORRT=ON
            cmake ..
            make -j4
        cd ../python
            sudo python3 setup.py install --user
fi
