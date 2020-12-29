cmake_minimum_required(VERSION 3.5)
project(AWS_Stream_SDK)
set(SRC_DIR awstreamer)

option(BUILD_METADATA "Build custom GStreamer metadata" ON)
option(BUILD_KVS "Build KVS GStreamer plug-in" OFF)
option(BUILD_KVS_WEBRTC "Build KVS WebRTC plug-in" OFF)
option(BUILD_CVML "Build CVML filter" OFF)
option(BUILD_NEO_DLR "Build SageMaker NEO runtime" OFF)
option(BUILD_MXNET "Build MXnet GStreamer plug-in" OFF)
option(BUILD_TESTS "Build tests" ON)

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

add_subdirectory(${SRC_DIR})

# Package all files into a separate directory
if (DEFINED PYTHON_PACKAGE_DIR)
    set(PYTHON_PACKAGE_DIR ${PYTHON_PACKAGE_DIR}/${SRC_DIR})
else()
    set(PYTHON_PACKAGE_DIR ${CMAKE_BINARY_DIR}/${SRC_DIR}_py)
endif()
message("-- PYTHON_PACKAGE_DIR: \t\t" ${PYTHON_PACKAGE_DIR})

# Copy python scripts
file(GLOB PY_FILES "${CMAKE_SOURCE_DIR}/${SRC_DIR}/*.py")
file(COPY ${PY_FILES} DESTINATION ${PYTHON_PACKAGE_DIR})

# Copy python plug-ins
file(GLOB PY_PLUGINS "${CMAKE_SOURCE_DIR}/${SRC_DIR}/gst_plugins/python/*.py")
file(COPY ${PY_PLUGINS} DESTINATION ${CMAKE_BINARY_DIR}/${SRC_DIR}/gst_plugins/python/)

# Copy metadata
file(GLOB PY_METADATA "${CMAKE_SOURCE_DIR}/${SRC_DIR}/gst_metadata/*.py")
file(COPY ${PY_METADATA} DESTINATION ${CMAKE_BINARY_DIR}/${SRC_DIR}/gst_metadata_lib/)

add_custom_target(COPY_GST_PIPELINE ALL
    COMMAND ${CMAKE_COMMAND} -E copy_directory ${CMAKE_SOURCE_DIR}/${SRC_DIR}/gst_pipeline ${PYTHON_PACKAGE_DIR}/gst_pipeline)

add_custom_target(COPY_GST_CONFIGURER ALL
    COMMAND ${CMAKE_COMMAND} -E copy_directory ${CMAKE_SOURCE_DIR}/${SRC_DIR}/gst_configurer ${PYTHON_PACKAGE_DIR}/gst_configurer)

add_custom_target(COPY_GST_VIEWER ALL
    COMMAND ${CMAKE_COMMAND} -E copy_directory ${CMAKE_SOURCE_DIR}/${SRC_DIR}/gst_viewer ${PYTHON_PACKAGE_DIR}/gst_viewer)

add_custom_target(COPY_UTILS ALL
    COMMAND ${CMAKE_COMMAND} -E copy_directory ${CMAKE_SOURCE_DIR}/${SRC_DIR}/utils ${PYTHON_PACKAGE_DIR}/utils)

add_custom_target(COPY_GST_METADATA ALL
    COMMAND ${CMAKE_COMMAND} -E copy_directory ${CMAKE_BINARY_DIR}/${SRC_DIR}/gst_metadata_lib ${PYTHON_PACKAGE_DIR}/gst_metadata)

add_custom_target(COPY_GST_PLUGINS ALL
    COMMAND ${CMAKE_COMMAND} -E copy_directory ${CMAKE_BINARY_DIR}/${SRC_DIR}/gst_plugins ${PYTHON_PACKAGE_DIR}/gst_plugins)

if (BUILD_METADATA)
    add_dependencies(COPY_GST_METADATA gst_objects_info_meta)
endif (BUILD_METADATA)

if (BUILD_KVS)
    add_dependencies(COPY_GST_PLUGINS KVS COPY_LIB_GST_KVS_SINK COPY_LIB_KINESIS_VIDEO_PRODUCER)
endif (BUILD_KVS)

if (BUILD_KVS_WEBRTC)
    add_dependencies(COPY_GST_PLUGINS KVS_WEBRTC COPY_LIB_GST_KVS_WEBRTC COPY_APP_KVS_WEBRTC_CLIENT)
endif (BUILD_KVS_WEBRTC)

if (BUILD_MXNET)
    add_dependencies(COPY_GST_PLUGINS MXNET)
endif (BUILD_MXNET)

# Build tests
if (BUILD_TESTS)
    # Macro definition to get list of subdirectories
    MACRO(SUBDIRLIST result curdir)
        FILE(GLOB children RELATIVE ${curdir} ${curdir}/*)
        SET(dirlist "")
        FOREACH(child ${children})
            IF(IS_DIRECTORY ${curdir}/${child})
            LIST(APPEND dirlist ${child})
            ENDIF()
        ENDFOREACH()
        SET(${result} ${dirlist})
    ENDMACRO()

    # Get list of subdirectories in examples folder
    SUBDIRLIST(SUBDIRS ${CMAKE_SOURCE_DIR}/examples)

    # Remove and copy awstreamer to each subdirectory
    FOREACH(subdir ${SUBDIRS})
        string(TOUPPER COPY_PACKAGE_TO_${subdir} TARGET_NAME)
        add_custom_target(${TARGET_NAME} ALL
            COMMAND ${CMAKE_COMMAND} -E remove_directory ${CMAKE_SOURCE_DIR}/examples/${subdir}/awstreamer
            COMMAND ${CMAKE_COMMAND} -E copy_directory ${PYTHON_PACKAGE_DIR} ${CMAKE_SOURCE_DIR}/examples/${subdir}/awstreamer
            DEPENDS COPY_GST_PLUGINS COPY_GST_METADATA COPY_UTILS COPY_GST_VIEWER COPY_GST_PIPELINE
        )
    ENDFOREACH()
endif (BUILD_TESTS)
