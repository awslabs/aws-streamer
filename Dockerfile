# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

FROM ubuntu:18.04

USER root

ENV DEBIAN_FRONTEND noninteractive

RUN /usr/bin/apt-get update && \
	/usr/bin/apt-get install -y curl && \
	curl -sL https://deb.nodesource.com/setup_10.x | bash - && \
	/usr/bin/apt-get update && \
	/usr/bin/apt-get upgrade -y && \
	/usr/bin/apt-get install -y nodejs pulseaudio xvfb xdotool unzip

RUN apt-get update && apt-get -y --no-install-recommends install \
    sudo \
    vim \
    wget \
    zip \
    build-essential \
    pkg-config \
    python3.7 \
    python3-pip \
    python3.7-dev \
    python3.7-venv \
    python3-dev \
    python3-numpy \
    python3-matplotlib \
    x11-apps

RUN apt-get -y --no-install-recommends install \
    git \
    cmake \
    autoconf \
    automake \
    libtool \
    libssl-dev \
    libopenexr-dev \
    libpng-dev \
    libjpeg-dev \
    libopenexr-dev \
    libtiff-dev \
    libopenblas-dev \
    libwebp-dev \
    libpoco-dev \
    libdc1394-22-dev \
    gstreamer-1.0 \
    gstreamer1.0-dev \
    libgstreamer1.0-0 \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    gstreamer1.0-doc \
    gstreamer1.0-tools \
    gstreamer1.0-x \
    gstreamer1.0-alsa \
    gstreamer1.0-gl \
    gstreamer1.0-gtk3 \
    gstreamer1.0-qt5 \
    gstreamer1.0-pulseaudio \
    python-gst-1.0 \
    libgirepository1.0-dev \
    libgstreamer-plugins-base1.0-dev \
    libcairo2-dev \
    gir1.2-gstreamer-1.0 \
    python3-gi \
    python-gi-dev \
    virtualenv

RUN apt -y autoremove

RUN pip3 install wheel pip setuptools

COPY . /aws-streamer

RUN pip3 install -r /aws-streamer/requirements.txt

RUN ["/bin/bash", "/aws-streamer/build.sh", "-DBUILD_KVS=ON"]

RUN ["/bin/ls", "-la", "/aws-streamer/examples/test_app/awstreamer/gst_plugins/kvs"]

WORKDIR /aws-streamer
RUN chmod +x /aws-streamer/examples/serverless/run.sh
ENTRYPOINT ["/aws-streamer/examples/serverless/run.sh"]
