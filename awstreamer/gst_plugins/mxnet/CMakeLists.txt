cmake_minimum_required(VERSION 3.2)
set(CMAKE_CXX_STANDARD 17)
project(mxnet)
set(EXEC_NAME mxnet)

if("${CMAKE_CXX_COMPILER_ID}" STREQUAL "GNU")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fPIC")
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -fPIC")
endif()

find_package(PkgConfig REQUIRED)
find_package(OpenCV REQUIRED)

if (NOT GST_METADATA_DIR)
  set(GST_METADATA_DIR $ENV{GST_METADATA_DIR})
endif()
message("-- GST_METADATA_DIR: \t\t" ${GST_METADATA_DIR})

if (SUBPROJECT_INSTALL_PREFIX)
  set(_SUBPROJECT_INSTALL_PREFIX ${SUBPROJECT_INSTALL_PREFIX}/ )
else()
  set(_SUBPROJECT_INSTALL_PREFIX . )
endif()
message("-- MXNET_INSTALL_DIR: \t" ${_SUBPROJECT_INSTALL_PREFIX})

set(MXNET_ROOT ${CMAKE_CURRENT_LIST_DIR}/incubator-mxnet)

externalproject_add(MXNET
    SOURCE_DIR            ${MXNET_ROOT}
    GIT_REPOSITORY        https://github.com/apache/incubator-mxnet.git
    GIT_TAG               1.6.0
    GIT_SHALLOW           TRUE
    BUILD_COMMAND         ${MAKE_EXE} USE_OPENCV=0 USE_BLAS=openblas USE_CPP_PACKAGE=1
    INSTALL_DIR           ${CMAKE_CURRENT_BINARY_DIR}
    CMAKE_ARGS            -DCMAKE_INSTALL_PREFIX=${CMAKE_CURRENT_BINARY_DIR}
)

ExternalProject_Get_property(MXNET INSTALL_DIR)
set(MXNET_INSTALL_DIR ${INSTALL_DIR})
message("-- MXNET_INSTALL_DIR: \t\t" ${MXNET_INSTALL_DIR})
message("-- MXNET_ROOT: \t\t\t" ${MXNET_ROOT})

ExternalProject_Get_property(MXNET BINARY_DIR)
set(MXNET_BUILD_DIR ${BINARY_DIR})
message("-- MXNET_BUILD_DIR: \t\t" ${MXNET_BUILD_DIR})

file(GLOB LIB_MXNET "${MXNET_BUILD_DIR}/libmxnet.*")
file(COPY ${LIB_MXNET} DESTINATION ${_SUBPROJECT_INSTALL_PREFIX})

# -- MXNet
include_directories(
  ${MXNET_ROOT}/include
  ${MXNET_ROOT}/cpp-package/include
  ${MXNET_ROOT}/3rdparty/dlpack/include
  ${MXNET_ROOT}/3rdparty/dmlc-core/include
  ${MXNET_ROOT}/3rdparty/mkldnn/include
  ${MXNET_ROOT}/3rdparty/mshadow
  ${MXNET_ROOT}/3rdparty/tvm/nnvm/include
  ${CMAKE_CURRENT_LIST_DIR}/src
)

# -- GStreamer
set(GSTREAMER_MINIMUM_VERSION 1.0.5)
pkg_check_modules(GST1_TEST gstreamer-1.0)
pkg_check_modules (GST_VIDEO REQUIRED gstreamer-video-1.0)
pkg_check_modules(GSTREAMER REQUIRED gstreamer-1.0)
pkg_check_modules(GSTREAMER-APP REQUIRED gstreamer-app-1.0)
pkg_check_modules(GSTREAMER-AUDIO REQUIRED gstreamer-audio-1.0)
pkg_check_modules(GSTREAMER-VIDEO REQUIRED gstreamer-video-1.0)
pkg_check_modules(GSTREAMER-PBUTILS REQUIRED gstreamer-pbutils-1.0)
pkg_check_modules(GSTREAMER-FFT REQUIRED gstreamer-fft-1.0)
add_definitions(-DGST_API_VERSION_1=1)


include_directories(
  ${GSTREAMER_INCLUDE_DIRS}
  ${GSTREAMER-APP_INCLUDE_DIRS}
  ${GSTREAMER-AUDIO_INCLUDE_DIRS}
  ${GSTREAMER-VIDEO_INCLUDE_DIRS}
  ${GSTREAMER-PBUTILS_INCLUDE_DIRS}
  ${GSTREAMER-FFT_INCLUDE_DIRS}
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${GST_METADATA_DIR}
)

set(OPEN_SRC_INCLUDE_DIRS
        ${GLIB2_INCLUDE_DIRS}
        ${GST_APP_INCLUDE_DIRS}
        ${GST_VIDEO_INCLUDE_DIRS}
        ${GST_INCLUDE_DIRS}
        ${GOBJ2_INCLUDE_DIRS}
        ${GST_CHECK_INCLUDE_DIRS}
        ${GST_BASE_INCLUDE_DIRS}
        ${CURL_INCLUDE_DIRS}
        ${CRYPTO_INCLUDE_DIRS}
        ${OpenCV_INCLUDE_DIRS}
)

set(OPEN_SRC_LIBRARY_DIRS
        ${GLIB2_LIBRARY_DIRS}
        ${GST_APP_LIBRARY_DIRS}
        ${GST_VIDEO_LIBRARY_DIRS}
        ${GST_LIBRARY_DIRS}
        ${GOBJ2_LIBRARY_DIRS}
        ${GST_CHECK_LIBRARY_DIRS}
        ${GST_BASE_LIBRARY_DIRS}
        ${CURL_LIBRARY_DIRS}
        ${CRYPTO_LIBRARY_DIRS}
        ${MXNET_ROOT}
)

set(GST_PLUGIN_LIBRARIES
        ${GST_LIBRARIES}
        ${GST_APP_LIBRARIES}
        ${GST_VIDEO_LIBRARIES}
        ${GLIB2_LIBRARIES}
        ${GOBJ2_LIBRARIES}
        ${GST_BASE_LIBRARIES}
        ${CURL_LIBRARIES}
        ${CRYPTO_LIBRARIES}
        ${OpenCV_LIBS}
        # ${MXNET_LIBS}
        ${GSTMETADATA_LIB}
)

set(GST_PLUGIN_SOURCE_FILES
        ${CMAKE_CURRENT_SOURCE_DIR}/src/gstmxnet.cpp
        ${CMAKE_CURRENT_SOURCE_DIR}/src/gstmxnet.h
        ${CMAKE_CURRENT_SOURCE_DIR}/src/common.hpp
        ${CMAKE_CURRENT_SOURCE_DIR}/src/ImageProcessor.cpp
        ${CMAKE_CURRENT_SOURCE_DIR}/src/ImageProcessor.h)

include_directories(${OPEN_SRC_INCLUDE_DIRS})
link_directories(${OPEN_SRC_LIBRARY_DIRS})

add_library(gstmxnet MODULE ${GST_PLUGIN_SOURCE_FILES})
target_include_directories(gstmxnet PRIVATE ${GST_INCLUDE_DIRS})
target_link_libraries(gstmxnet ${GST_PLUGIN_LIBRARIES})
target_link_libraries(gstmxnet gst_objects_info_meta)
