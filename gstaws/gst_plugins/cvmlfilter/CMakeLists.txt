cmake_minimum_required(VERSION 3.2)
set(CMAKE_CXX_STANDARD 14)
project(cvmlfilter)

set(EXEC_NAME cvmlfilter)

message(STATUS "System name is ${CMAKE_SYSTEM_NAME}")
STRING(TOLOWER "${CMAKE_SYSTEM_NAME}" CMAKE_SYSTEM_NAME_LOWER_CASE)
STRING(TOLOWER "${CMAKE_BUILD_TYPE}" CMAKE_BUILD_TYPE_LOWER)

if("${CMAKE_CXX_COMPILER_ID}" STREQUAL "GNU")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fPIC")
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -fPIC")
endif()

set(THREADS_PREFER_PTHREAD_FLAG ON)
find_package(Threads)

set(EXE_LIBRARIES Threads::Threads ${CMAKE_DL_LIBS})

if (NOT ${CMAKE_SYSTEM_NAME} MATCHES "Darwin" AND NOT ${CMAKE_SYSTEM_NAME} MATCHES "Windows")
    set(EXE_LIBRARIES ${EXE_LIBRARIES} rt)
endif ()

if(${CMAKE_SYSTEM_NAME} MATCHES "Windows")
  set(CMAKE_MODULE_LINKER_FLAGS "${CMAKE_MODULE_LINKER_FLAGS} -Wl,--export-all-symbols")
  add_definitions(-DCURL_STATICLIB -DWIN32_LEAN_AND_MEAN -DVC_EXTRALEAN -D_HAS_ITERATOR_DEBUGGING=0)
endif()

find_package(PkgConfig REQUIRED)
find_package( OpenCV REQUIRED )

set(GSTREAMER_MINIMUM_VERSION 1.0.5)

pkg_check_modules(GST1_TEST gstreamer-1.0)
pkg_check_modules (GST_VIDEO REQUIRED gstreamer-video-1.0)
if ( GST1_TEST_FOUND AND NOT ${GST1_TEST_VERSION} VERSION_LESS ${GSTREAMER_MINIMUM_VERSION} )
    pkg_check_modules(GSTREAMER REQUIRED gstreamer-1.0)
    pkg_check_modules(GSTREAMER-APP REQUIRED gstreamer-app-1.0)
    pkg_check_modules(GSTREAMER-AUDIO REQUIRED gstreamer-audio-1.0)
    pkg_check_modules(GSTREAMER-VIDEO REQUIRED gstreamer-video-1.0)
    pkg_check_modules(GSTREAMER-PBUTILS REQUIRED gstreamer-pbutils-1.0)
    pkg_check_modules(GSTREAMER-FFT REQUIRED gstreamer-fft-1.0)
    add_definitions(-DGST_API_VERSION_1=1)
else()
    # fallback to gstreamer-0.10
    unset(GSTREAMER_MINIMUM_VERSION)
    pkg_check_modules(GSTREAMER REQUIRED gstreamer-0.10)
    pkg_check_modules(GSTREAMER-APP REQUIRED gstreamer-app-0.10)
    pkg_check_modules(GSTREAMER-AUDIO REQUIRED gstreamer-audio-0.10)
    pkg_check_modules(GSTREAMER-VIDEO REQUIRED gstreamer-video-0.10)
    pkg_check_modules(GSTREAMER-FFT REQUIRED gstreamer-fft-0.10)
    set_source_files_properties(WebKitWebAudioSourceGStreamer.cpp PROPERTIES COMPILE_DEFINITIONS "GLIB_DISABLE_DEPRECATION_WARNINGS=1")
endif()

include_directories(
  ${GSTREAMER_INCLUDE_DIRS}
  ${GSTREAMER-APP_INCLUDE_DIRS}
  ${GSTREAMER-AUDIO_INCLUDE_DIRS}
  ${GSTREAMER-VIDEO_INCLUDE_DIRS}
  ${GSTREAMER-PBUTILS_INCLUDE_DIRS}
  ${GSTREAMER-FFT_INCLUDE_DIRS}
  ${CMAKE_CURRENT_SOURCE_DIR}
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
        ${CRYPTO_LIBRARY_DIRS})

set(KVSSINK_LIBRARIES
        ${GST_LIBRARIES}
        ${GST_APP_LIBRARIES}
        ${GST_VIDEO_LIBRARIES}
        ${GLIB2_LIBRARIES}
        ${GOBJ2_LIBRARIES}
        ${GST_BASE_LIBRARIES}
        ${CURL_LIBRARIES}
        ${CRYPTO_LIBRARIES}
        ${OpenCV_LIBS}
)

set(KVSSINK_DEMO_LIBRARIES
        ${GLIB2_LIBRARIES}
        ${GST_LIBRARIES}
        ${GOBJ2_LIBRARIES}
        ${EXE_LIBRARIES})

set(GST_PLUGIN_SOURCE_FILES
        ${CMAKE_CURRENT_SOURCE_DIR}/gstcvmlfilter.cpp
        ${CMAKE_CURRENT_SOURCE_DIR}/gstcvmlfilter.h
        ${CMAKE_CURRENT_SOURCE_DIR}/ImageProcessor.cpp
        ${CMAKE_CURRENT_SOURCE_DIR}/ImageProcessor.h)

include_directories(${OPEN_SRC_INCLUDE_DIRS})
link_directories(${OPEN_SRC_LIBRARY_DIRS})

add_library(gstcvmlfilter MODULE ${GST_PLUGIN_SOURCE_FILES})
target_include_directories(gstcvmlfilter PRIVATE ${GST_INCLUDE_DIRS})
target_link_libraries(gstcvmlfilter ${KVSSINK_LIBRARIES})
