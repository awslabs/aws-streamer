#!/bin/bash

# full_path=$(realpath $0)
# dir_path=$(dirname $full_path)

if [ ! -d gst-python ]; then

    git clone https://github.com/GStreamer/gst-python.git
fi

if [ ! -d gst-python/build ]; then

    # After PyGObject (https://lazka.github.io/pgi-docs/) installed
    # Run current script to override Gstreamer related Scripts

    LIBPYTHONPATH=""
    PYTHON=${PYTHON:-/usr/bin/python3}
    GST_VERSION=${GST_VERSION:-$(gst-launch-1.0 --version | grep version | tr -s ' ' '\n' | tail -1)}

    # Ensure pygst to be installed in current environment
    LIBPYTHON=$($PYTHON -c 'from distutils import sysconfig; print(sysconfig.get_config_var("LDLIBRARY"))')
    LIBPYTHONPATH=$(dirname $(ldconfig -p | grep -w $LIBPYTHON | head -1 | tr ' ' '\n' | grep /))

    GST_PREFIX=${GST_PREFIX:-$(dirname $(dirname $(which python)))}

    echo "Python Executable: $PYTHON"
    echo "Python Library Path: $LIBPYTHONPATH"
    echo "Current Python Path $GST_PREFIX"
    echo "Gstreamer Version: $GST_VERSION"

    cd gst-python

        export PYTHON=$PYTHON
        git checkout $GST_VERSION

        ./autogen.sh --disable-gtk-doc --noconfigure
        ./configure --with-libpython-dir=$LIBPYTHONPATH --prefix $GST_PREFIX
        make
        # make install

        # # pip3 install meson
        # # sudo apt install ninja-build
        # mkdir build
        # cd build
        #     meson ..
        #     make
        #     make install
        #     # ninja
        #     # ninja install
        # cd ..
    cd ..

fi
