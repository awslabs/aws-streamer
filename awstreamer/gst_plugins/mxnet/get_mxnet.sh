
if [ ! -d incubator-mxnet ]; then
    git clone --recursive -b 1.6.0 https://github.com/apache/incubator-mxnet.git --depth 1
fi

if [ ! -d incubator-mxnet/build ]; then
    cd incubator-mxnet
        make USE_OPENCV=1 USE_BLAS=openblas USE_CPP_PACKAGE=1
        # USE_CUDA=1 USE_TENSORRT=1
fi
