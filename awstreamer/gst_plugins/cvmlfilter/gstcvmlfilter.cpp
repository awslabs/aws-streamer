
// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * SECTION:element-gstcvmlfilter
 *
 * The cvmlfilter element does CV/ML task on RGB frame stuff.
 *
 * <refsect2>
 * <title>Example launch line</title>
 * |[
 * gst-launch-1.0 -v fakesrc ! cvmlfilter ! fakesink
 * ]|
 * cvmlfilter will process input of fakesrc and output it over to fakesink
 * </refsect2>
 */

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include <vector>
#include <map>

#include <gst/gst.h>
#include <gst/video/video.h>
#include <gst/video/gstvideofilter.h>
#include "gstcvmlfilter.h"


GST_DEBUG_CATEGORY_STATIC(gst_cvmlfilter_debug_category);
#define GST_CAT_DEFAULT gst_cvmlfilter_debug_category

// Helper methods

gboolean setParams(GQuark field_id, const GValue *value, gpointer g_ptr_user_map) {
    std::map<std::string, std::string> *target_map = reinterpret_cast<std::map<std::string, std::string> *>(g_ptr_user_map);
    std::string field_str = std::string(g_quark_to_string (field_id));
    std::string value_str;
    gboolean ret = TRUE;

    if (!G_VALUE_HOLDS_STRING(value)) {
        GST_ERROR("Value should be of \"String\" type for %s\n", field_str.c_str());
        ret = FALSE;
        goto CleanUp;
    }
    value_str = std::string(g_value_get_string(value));
    if (value_str.empty() || field_str.empty()) {
        GST_ERROR("Field and value should not be empty. field: %s , value: %s\n", field_str.c_str(), value_str.c_str());
        ret = FALSE;
        goto CleanUp;
    }
    target_map->insert(std::pair<std::string,std::string>(field_str, value_str));

CleanUp:
    return ret;
}

gboolean gstructToMap(GstStructure *g_struct, std::map<std::string, std::string> *user_map) {
    std::map<std::string, std::string> temp;
    gboolean ret = gst_structure_foreach (g_struct, setParams, user_map);
    if (ret) { // if conversion failed, user_map will be unchanged
        user_map->insert(temp.begin(), temp.end());
    }
    return ret;
}

// Helper methods - END

/* prototypes */

static void gst_cvmlfilter_set_property(GObject * object, guint property_id, const GValue * value, GParamSpec * pspec);
static void gst_cvmlfilter_get_property(GObject * object, guint property_id, GValue * value, GParamSpec * pspec);
static void gst_cvmlfilter_dispose(GObject * object);
static void gst_cvmlfilter_finalize(GObject * object);

static gboolean gst_cvmlfilter_start(GstBaseTransform * trans);
static gboolean gst_cvmlfilter_stop(GstBaseTransform * trans);
static gboolean gst_cvmlfilter_set_info(GstVideoFilter * filter, GstCaps * incaps, GstVideoInfo * in_info, GstCaps * outcaps, GstVideoInfo * out_info);
static GstFlowReturn gst_cvmlfilter_transform_frame(GstVideoFilter * filter, GstVideoFrame * inframe, GstVideoFrame * outframe);
static GstFlowReturn gst_cvmlfilter_transform_frame_ip(GstVideoFilter * filter, GstVideoFrame * frame);

static guint processing_complete_signal = 0;

// Properties

#define DEFAULT_REGION "us-west-2"

enum {
  PROP_0,
  PROP_AWS_REGION,
  PROP_FILTER_TAGS
};

/* pad templates */

/* FIXME: add/remove formats you can handle */
#define VIDEO_SRC_CAPS GST_VIDEO_CAPS_MAKE("{ BGR }")

/* FIXME: add/remove formats you can handle */
#define VIDEO_SINK_CAPS GST_VIDEO_CAPS_MAKE("{ BGR }")


/* class initialization */

G_DEFINE_TYPE_WITH_CODE (GstCvmlFilter, gst_cvmlfilter, GST_TYPE_VIDEO_FILTER,
  GST_DEBUG_CATEGORY_INIT (gst_cvmlfilter_debug_category, "cvmlfilter", 0,
  "debug category for cvmlfilter element"));

static void gst_cvmlfilter_class_init(GstCvmlFilterClass * klass) {
    GObjectClass *gobject_class = G_OBJECT_CLASS (klass);
    GstBaseTransformClass *base_transform_class = GST_BASE_TRANSFORM_CLASS (klass);
    GstVideoFilterClass *video_filter_class = GST_VIDEO_FILTER_CLASS (klass);

    /* Setting up pads and setting metadata should be moved to
      base_class_init if you intend to subclass this class. */
    gst_element_class_add_pad_template (GST_ELEMENT_CLASS(klass),
        gst_pad_template_new ("src", GST_PAD_SRC, GST_PAD_ALWAYS,
          gst_caps_from_string (VIDEO_SRC_CAPS)));
    gst_element_class_add_pad_template (GST_ELEMENT_CLASS(klass),
        gst_pad_template_new ("sink", GST_PAD_SINK, GST_PAD_ALWAYS,
          gst_caps_from_string (VIDEO_SINK_CAPS)));

    gst_element_class_set_static_metadata (GST_ELEMENT_CLASS(klass),
        "CVML Filter", "Generic", "CV/ML filtering plug-in",
        "Bartek Pawlik <pawlikb@amazon.com>");

    gobject_class->set_property = gst_cvmlfilter_set_property;
    gobject_class->get_property = gst_cvmlfilter_get_property;
    gobject_class->dispose = gst_cvmlfilter_dispose;
    gobject_class->finalize = gst_cvmlfilter_finalize;
    base_transform_class->start = GST_DEBUG_FUNCPTR (gst_cvmlfilter_start);
    base_transform_class->stop = GST_DEBUG_FUNCPTR (gst_cvmlfilter_stop);
    video_filter_class->set_info = GST_DEBUG_FUNCPTR (gst_cvmlfilter_set_info);
    video_filter_class->transform_frame = GST_DEBUG_FUNCPTR (gst_cvmlfilter_transform_frame);
    video_filter_class->transform_frame_ip = GST_DEBUG_FUNCPTR (gst_cvmlfilter_transform_frame_ip);

    g_object_class_install_property(gobject_class, PROP_AWS_REGION,
      g_param_spec_string ("aws-region", "AWS Region", "AWS Region", DEFAULT_REGION,
      (GParamFlags) (G_PARAM_READWRITE | G_PARAM_STATIC_STRINGS)));

    g_object_class_install_property(gobject_class, PROP_FILTER_TAGS,
      g_param_spec_boxed ("stream-tags", "Stream Tags",
                          "key-value pair that you can define and assign to each stream",
                          GST_TYPE_STRUCTURE, (GParamFlags) (G_PARAM_READWRITE | G_PARAM_STATIC_STRINGS)));

    processing_complete_signal =
        g_signal_new ("processing-complete", G_TYPE_FROM_CLASS(klass),
          G_SIGNAL_RUN_LAST, 0, NULL, NULL, NULL,
          G_TYPE_NONE, 1, G_TYPE_UINT);
}

static void gst_cvmlfilter_init(GstCvmlFilter *cvmlfilter) {
    cvmlfilter->aws_region = g_strdup(DEFAULT_REGION);
    cvmlfilter->filter_tags = NULL;
    cvmlfilter->imageProcessor = new ImageProcessor();
}

void gst_cvmlfilter_set_property(GObject * object, guint property_id, const GValue * value, GParamSpec * pspec) {
    GstCvmlFilter *cvmlfilter = GST_CVMLFILTER (object);
    GST_DEBUG_OBJECT (cvmlfilter, "set_property");

    switch (property_id) {
    case PROP_AWS_REGION:
        g_free(cvmlfilter->aws_region);
        cvmlfilter->aws_region = g_strdup (g_value_get_string (value));
        break;
    case PROP_FILTER_TAGS: {
        const GstStructure *s = gst_value_get_structure(value);

        if (cvmlfilter->filter_tags) {
            gst_structure_free(cvmlfilter->filter_tags);
        }
        cvmlfilter->filter_tags = s ? gst_structure_copy(s) : NULL;

        // Parse input configuration
        std::map<std::string, std::string> filter_tags;
        if (cvmlfilter->filter_tags) {
            gboolean ret;
            ret = gstructToMap(cvmlfilter->filter_tags, &filter_tags);
            if (!ret) {
                GST_WARNING("Failed to parse stream tags");
                break;
            }
        }
        cvmlfilter->imageProcessor->setParams(filter_tags);
        break;
    }
    default:
        G_OBJECT_WARN_INVALID_PROPERTY_ID (object, property_id, pspec);
        break;
    }
}

void gst_cvmlfilter_get_property(GObject * object, guint property_id, GValue * value, GParamSpec * pspec) {
    GstCvmlFilter *cvmlfilter = GST_CVMLFILTER (object);
    GST_DEBUG_OBJECT (cvmlfilter, "get_property");

    switch (property_id) {
    case PROP_AWS_REGION:
        g_value_set_string (value, cvmlfilter->aws_region);
        break;
    case PROP_FILTER_TAGS:
        gst_value_set_structure (value, cvmlfilter->filter_tags);
        break;
    default:
        G_OBJECT_WARN_INVALID_PROPERTY_ID (object, property_id, pspec);
        break;
    }
}

void gst_cvmlfilter_dispose(GObject * object) {
    GstCvmlFilter *cvmlfilter = GST_CVMLFILTER (object);

    GST_DEBUG_OBJECT (cvmlfilter, "dispose");

    /* clean up as possible.  may be called multiple times */

    G_OBJECT_CLASS (gst_cvmlfilter_parent_class)->dispose (object);
}

void gst_cvmlfilter_finalize(GObject * object) {
    GstCvmlFilter *cvmlfilter = GST_CVMLFILTER (object);

    GST_DEBUG_OBJECT (cvmlfilter, "finalize");

    /* clean up object here */
    if (cvmlfilter->filter_tags) {
        gst_structure_free(cvmlfilter->filter_tags);
    }

    if (cvmlfilter->imageProcessor) {
        delete cvmlfilter->imageProcessor;
    }

    G_OBJECT_CLASS (gst_cvmlfilter_parent_class)->finalize (object);
}

static gboolean gst_cvmlfilter_start(GstBaseTransform * trans) {
    GstCvmlFilter *cvmlfilter = GST_CVMLFILTER (trans);

    GST_DEBUG_OBJECT (cvmlfilter, "start");

    return TRUE;
}

static gboolean gst_cvmlfilter_stop(GstBaseTransform * trans) {
    GstCvmlFilter *cvmlfilter = GST_CVMLFILTER (trans);

    GST_DEBUG_OBJECT (cvmlfilter, "stop");

    return TRUE;
}

static gboolean gst_cvmlfilter_set_info(GstVideoFilter * filter, GstCaps * incaps,
    GstVideoInfo * in_info, GstCaps * outcaps, GstVideoInfo * out_info) {
    GstCvmlFilter *cvmlfilter = GST_CVMLFILTER (filter);

    cvmlfilter->img_width = GST_VIDEO_INFO_WIDTH(in_info);
    cvmlfilter->img_height = GST_VIDEO_INFO_HEIGHT(in_info);

    GST_DEBUG_OBJECT (cvmlfilter, "set_info");

    return TRUE;
}

/* transform */
static GstFlowReturn gst_cvmlfilter_transform_frame(GstVideoFilter * filter, GstVideoFrame * inframe,
    GstVideoFrame * outframe) {
    GstCvmlFilter *cvmlfilter = GST_CVMLFILTER (filter);

    GST_DEBUG_OBJECT (cvmlfilter, "transform_frame");
    GST_DEBUG(">>>>> CVML filter in action! <<<<<");

    // Process input frame
    cv::Mat img_src(cvmlfilter->img_height, cvmlfilter->img_width, CV_8UC3, inframe->data[0]);
    cv::Mat img_dst(cvmlfilter->img_height, cvmlfilter->img_width, CV_8UC3, outframe->data[0]);
    PipelineAction action = cvmlfilter->imageProcessor->process(img_src, img_dst);

    GST_LOG_OBJECT (cvmlfilter, "Signaling from CVML!!!");
    g_signal_emit(G_OBJECT (cvmlfilter), processing_complete_signal, 0, action);

    return GST_FLOW_OK;
}

static GstFlowReturn gst_cvmlfilter_transform_frame_ip(GstVideoFilter * filter, GstVideoFrame * frame) {
    GstCvmlFilter *cvmlfilter = GST_CVMLFILTER (filter);

    GST_DEBUG_OBJECT (cvmlfilter, "transform_frame_ip");

    return GST_FLOW_OK;
}

static gboolean plugin_init(GstPlugin * plugin) {
    /* FIXME Remember to set the rank if it's an element that is meant
      to be autoplugged by decodebin. */
    return gst_element_register (plugin, "cvmlfilter", GST_RANK_NONE, GST_TYPE_CVMLFILTER);
}

/* FIXME: these are normally defined by the GStreamer build system.
   If you are creating an element to be included in gst-plugins-*,
   remove these, as they're always defined.  Otherwise, edit as
   appropriate for your external plugin package. */
#ifndef VERSION
#define VERSION "0.0.1"
#endif
#ifndef PACKAGE
#define PACKAGE "CVML_package"
#endif
#ifndef PACKAGE_NAME
#define PACKAGE_NAME "CVML_package_name"
#endif
#ifndef GST_PACKAGE_ORIGIN
#define GST_PACKAGE_ORIGIN "http://amazon.com/"
#endif

GST_PLUGIN_DEFINE (GST_VERSION_MAJOR,
    GST_VERSION_MINOR,
    cvmlfilter,
    "CVML plugin description",
    plugin_init, VERSION, "LGPL", PACKAGE_NAME, GST_PACKAGE_ORIGIN)
