cmake_minimum_required(VERSION 3.5)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=gnu++0x -g -fpermissive")
set(CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/CMake;${CMAKE_MODULE_PATH}")
set(SRC_DIR ${CMAKE_CURRENT_SOURCE_DIR})

include(ExternalProject)
project(awstreamer)

option(BUILD_METADATA "Build custom GStreamer metadata" ON)
option(BUILD_KVS "Build KVS GStreamer plug-in" OFF)
option(BUILD_KVS_WEBRTC "Build KVS WebRTC plug-in" OFF)
option(BUILD_CVML "Build CVML filter" OFF)
option(BUILD_NEO_DLR "Build SageMaker NEO runtime" OFF)
option(BUILD_MXNET "Build MXnet GStreamer plug-in" OFF)

if (APPLE)
  message("-- APPLE \t\t\t= ON")
  set(CMAKE_MACOSX_RPATH ON)
  set(BUILD_METADATA OFF)
endif (APPLE)

execute_process(COMMAND uname OUTPUT_VARIABLE uname)
if (uname MATCHES "^MINGW")
  message("-- MINGW \t\t\t= ON")
  set(BUILD_METADATA OFF)
endif ()

if (BUILD_METADATA)
  message("-- BUILD_METADATA \t\t= ON")
else ()
  message("-- BUILD_METADATA \t\t= OFF")
endif (BUILD_METADATA)

if (BUILD_KVS)
  message("-- BUILD_KVS \t\t\t= ON")
  add_definitions(-DKVS_ENABLED)
else ()
  message("-- BUILD_KVS \t\t\t= OFF")
endif (BUILD_KVS)

if (BUILD_KVS_WEBRTC)
  message("-- BUILD_KVS_WEBRTC \t\t= ON")
  add_definitions(-DKVS_ENABLED)
else ()
  message("-- BUILD_KVS_WEBRTC \t\t= OFF")
endif (BUILD_KVS_WEBRTC)

if (BUILD_CVML)
  message("-- BUILD_CVML \t\t\t= ON")
else ()
  message("-- BUILD_CVML \t\t\t= OFF")
endif (BUILD_CVML)

if (BUILD_NEO_DLR)
  message("-- BUILD_NEO_DLR \t\t= ON")
else ()
  message("-- BUILD_NEO_DLR \t\t= OFF")
endif (BUILD_NEO_DLR)

if (BUILD_MXNET)
  message("-- BUILD_MXNET \t\t\t= ON")
else ()
  message("-- BUILD_MXNET \t\t\t= OFF")
endif (BUILD_MXNET)

set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} "${CMAKE_SOURCE_DIR}/cmake/Modules/")

if (BUILD_METADATA)
  set(GST_METADATA_DIR "${CMAKE_CURRENT_SOURCE_DIR}/gst_metadata")
  set(SUBPROJECT_INSTALL_PREFIX ${CMAKE_CURRENT_BINARY_DIR}/gst_metadata_lib CACHE STRING "Path in project")
  add_subdirectory(gst_metadata)
endif (BUILD_METADATA)

if (BUILD_KVS)
  externalproject_add(KVS
      SOURCE_DIR            ${CMAKE_CURRENT_SOURCE_DIR}/gst_plugins/kvs
      GIT_REPOSITORY        https://github.com/awslabs/amazon-kinesis-video-streams-producer-sdk-cpp.git
      CMAKE_ARGS            -DBUILD_GSTREAMER_PLUGIN=ON -DBUILD_DEPENDENCIES=ON
  )

  ExternalProject_Get_property(KVS BINARY_DIR)
  set(KVS_BUILD_DIR ${BINARY_DIR})
  set(KVS_DESTDIR ${CMAKE_CURRENT_BINARY_DIR}/gst_plugins/kvs)
  file(MAKE_DIRECTORY ${KVS_DESTDIR})

  message("-- KVS_BUILD_DIR: \t\t" ${KVS_BUILD_DIR})
  message("-- KVS_DEST_DIR: \t\t" ${KVS_DESTDIR})

  add_custom_target(COPY_LIB_GST_KVS_SINK ALL
      COMMAND ${CMAKE_COMMAND} -E copy "${KVS_BUILD_DIR}/libgstkvssink.*" ${KVS_DESTDIR}
      DEPENDS KVS
  )

  add_custom_target(COPY_LIB_KINESIS_VIDEO_PRODUCER ALL
      COMMAND ${CMAKE_COMMAND} -E copy "${KVS_BUILD_DIR}/libKinesisVideoProducer.*" ${KVS_DESTDIR}
      DEPENDS KVS
  )

endif (BUILD_KVS)

if (BUILD_KVS_WEBRTC)
  externalproject_add(KVS_WEBRTC
      SOURCE_DIR            ${CMAKE_CURRENT_SOURCE_DIR}/gst_plugins/kvs_webrtc
      GIT_REPOSITORY        https://github.com/awslabs/amazon-kinesis-video-streams-webrtc-sdk-c.git
      CMAKE_ARGS            -DBUILD_DEPENDENCIES=ON
  )

  ExternalProject_Get_property(KVS_WEBRTC BINARY_DIR)
  set(KVS_WEBRTC_BUILD_DIR ${BINARY_DIR})
  set(KVS_WEBRTC_DESTDIR ${CMAKE_CURRENT_BINARY_DIR}/gst_plugins/kvs_webrtc)
  file(MAKE_DIRECTORY ${KVS_WEBRTC_DESTDIR})

  message("-- KVS_WEBRTC_BUILD_DIR: \t" ${KVS_WEBRTC_BUILD_DIR})
  message("-- KVS_WEBRTC_DEST_DIR: \t" ${KVS_WEBRTC_DESTDIR})

  add_custom_target(COPY_LIB_GST_KVS_WEBRTC ALL
      COMMAND ${CMAKE_COMMAND} -E copy "${KVS_WEBRTC_BUILD_DIR}/libkvsWebrtc*" ${KVS_WEBRTC_DESTDIR}
      DEPENDS KVS_WEBRTC
  )

  add_custom_target(COPY_APP_KVS_WEBRTC_CLIENT ALL
      COMMAND ${CMAKE_COMMAND} -E copy "${KVS_WEBRTC_BUILD_DIR}/kvsWebrtcClient*" ${KVS_WEBRTC_DESTDIR}
      DEPENDS KVS_WEBRTC
  )

endif (BUILD_KVS_WEBRTC)

if (BUILD_NEO_DLR)
  add_custom_target(NEODLR ALL ${CMAKE_CURRENT_SOURCE_DIR}/gst_plugins/dlr/get_dlr.sh ${CMAKE_BINARY_DIR}
                    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/gst_plugins/dlr/)
endif (BUILD_NEO_DLR)

if (BUILD_MXNET)
  unset(SUBPROJECT_INSTALL_PREFIX)
  set(SUBPROJECT_INSTALL_PREFIX ${CMAKE_CURRENT_BINARY_DIR}/gst_plugins/mxnet CACHE STRING "Path in project")
  add_subdirectory(gst_plugins/mxnet)
endif (BUILD_MXNET)

if (BUILD_CVML)
  add_subdirectory(gst_plugins/cvmlfilter)
else ()
  set(gstcvmlfilter TRUE)
endif (BUILD_CVML)
