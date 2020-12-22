cmake_minimum_required(VERSION 2.8)

project (gst_metadata)
set(CMAKE_BUILD_TYPE Release)

include_directories(${CMAKE_CURRENT_SOURCE_DIR}/include)
add_library(gst_objects_info_meta SHARED gst_objects_info_meta.c)

# Gstreamer linkage
include(${CMAKE_ROOT}/Modules/FindPkgConfig.cmake)

# Set CMAKE_C_FLAGS variable with info from pkg-util
execute_process(COMMAND pkg-config --cflags gstreamer-1.0
                OUTPUT_VARIABLE CMAKE_C_FLAGS)
string(REPLACE "\n" "" CMAKE_C_FLAGS ${CMAKE_C_FLAGS})

# Set CMAKE_EXE_LINKER_FLAGS variable with info from pkg-util

execute_process(COMMAND pkg-config --libs gstreamer-1.0
                OUTPUT_VARIABLE CMAKE_EXE_LINKER_FLAGS)
string(REPLACE "\n" "" CMAKE_LINKER_FLAGS ${CMAKE_EXE_LINKER_FLAGS})

set_target_properties(gst_objects_info_meta
                      PROPERTIES COMPILE_FLAGS ${CMAKE_C_FLAGS}
                                 LINKER_FLAGS ${CMAKE_EXE_LINKER_FLAGS})

if (SUBPROJECT_INSTALL_PREFIX)
  set(_SUBPROJECT_INSTALL_PREFIX ${SUBPROJECT_INSTALL_PREFIX}/ )
else()
  set(_SUBPROJECT_INSTALL_PREFIX . )
endif()

message("-- GST_METADATA_INSTALL_DIR: \t" ${_SUBPROJECT_INSTALL_PREFIX})

set_target_properties(gst_objects_info_meta
    PROPERTIES
    ARCHIVE_OUTPUT_DIRECTORY ${_SUBPROJECT_INSTALL_PREFIX}
    LIBRARY_OUTPUT_DIRECTORY ${_SUBPROJECT_INSTALL_PREFIX}
    RUNTIME_OUTPUT_DIRECTORY ${_SUBPROJECT_INSTALL_PREFIX}
)
