/**
 * SECTION:element-gstmxnet
 *
 * The mxnet element does MXNet inference on RGB frame.
 *
 * <refsect2>
 * <title>Example launch line</title>
 * |[
 *  gst-launch-1.0 videotestsrc ! video/x-raw,format=RGBA,width=1280,height=720 ! videoconvert ! mxnet ! videoconvert ! fpsdisplaysink sync=false
 * ]|
 * mxnet will process input of fakesrc and output it over to fakesink
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
#include "gstmxnet.h"


GST_DEBUG_CATEGORY_STATIC(gst_mxnet_debug_category);
#define GST_CAT_DEFAULT gst_mxnet_debug_category

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

static void gst_mxnet_set_property(GObject * object, guint property_id, const GValue * value, GParamSpec * pspec);
static void gst_mxnet_get_property(GObject * object, guint property_id, GValue * value, GParamSpec * pspec);
static void gst_mxnet_dispose(GObject * object);
static void gst_mxnet_finalize(GObject * object);

static gboolean gst_mxnet_start(GstBaseTransform * trans);
static gboolean gst_mxnet_stop(GstBaseTransform * trans);
static gboolean gst_mxnet_set_info(GstVideoFilter * filter, GstCaps * incaps, GstVideoInfo * in_info, GstCaps * outcaps, GstVideoInfo * out_info);
static GstFlowReturn gst_mxnet_transform_frame(GstVideoFilter * filter, GstVideoFrame * inframe, GstVideoFrame * outframe);
static GstFlowReturn gst_mxnet_transform_frame_ip(GstVideoFilter * filter, GstVideoFrame * frame);

static guint processing_complete_signal = 0;

// Properties

#define DEFAULT_MODEL_FILE ""
#define DEFAULT_CLASS_FILE ""
#define DEFAULT_DEVICE_TYPE "cpu"
#define DEFAULT_IMAGE_SIZE 512

enum {
  PROP_0,
  PROP_MODEL_FILE,
  PROP_CLASS_FILE,
  PROP_DEVICE_TYPE,
  PROP_IMAGE_SIZE,
  PROP_FILTER_TAGS
};

/* pad templates */

/* FIXME: add/remove formats you can handle */
#define VIDEO_SRC_CAPS GST_VIDEO_CAPS_MAKE("{ BGR }")

/* FIXME: add/remove formats you can handle */
#define VIDEO_SINK_CAPS GST_VIDEO_CAPS_MAKE("{ BGR }")


/* class initialization */

G_DEFINE_TYPE_WITH_CODE (GstMXNet, gst_mxnet, GST_TYPE_VIDEO_FILTER,
  GST_DEBUG_CATEGORY_INIT (gst_mxnet_debug_category, "mxnet", 0,
  "debug category for mxnet element"));

static void gst_mxnet_class_init(GstMXNetClass * klass) {
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
        "MXNet inference filter", "Generic", "CV/ML filtering plug-in",
        "Bartek Pawlik <pawlikb@amazon.com>");

    gobject_class->set_property = gst_mxnet_set_property;
    gobject_class->get_property = gst_mxnet_get_property;
    gobject_class->dispose = gst_mxnet_dispose;
    gobject_class->finalize = gst_mxnet_finalize;
    base_transform_class->start = GST_DEBUG_FUNCPTR (gst_mxnet_start);
    base_transform_class->stop = GST_DEBUG_FUNCPTR (gst_mxnet_stop);
    video_filter_class->set_info = GST_DEBUG_FUNCPTR (gst_mxnet_set_info);
    video_filter_class->transform_frame = GST_DEBUG_FUNCPTR (gst_mxnet_transform_frame);
    video_filter_class->transform_frame_ip = GST_DEBUG_FUNCPTR (gst_mxnet_transform_frame_ip);

    g_object_class_install_property(gobject_class, PROP_MODEL_FILE,
      g_param_spec_string ("model-file", "Model file",
        "Basename of the model files: <model-file>-0000.params and <model-file>-symbol.json",
        DEFAULT_MODEL_FILE,
      (GParamFlags) (G_PARAM_READWRITE | G_PARAM_STATIC_STRINGS)));

    g_object_class_install_property(gobject_class, PROP_CLASS_FILE,
      g_param_spec_string ("class-file", "Class file",
      "Plain text file for class names, one name per line. Needed only for visualization.", DEFAULT_CLASS_FILE,
      (GParamFlags) (G_PARAM_READWRITE | G_PARAM_STATIC_STRINGS)));

    g_object_class_install_property(gobject_class, PROP_DEVICE_TYPE,
      g_param_spec_string ("device-type", "Device type",
      "Device type, cpu or gpu. You can also specify GPU index, e.g. gpu:0", DEFAULT_DEVICE_TYPE,
      (GParamFlags) (G_PARAM_READWRITE | G_PARAM_STATIC_STRINGS)));

    g_object_class_install_property(gobject_class, PROP_IMAGE_SIZE,
      g_param_spec_int ("image-size", "Image size", "Image size for inference", 32, G_MAXINT, DEFAULT_IMAGE_SIZE,
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

static void gst_mxnet_init(GstMXNet *mxnet) {
    mxnet->model_file = g_strdup(DEFAULT_MODEL_FILE);
    mxnet->klass_file = g_strdup(DEFAULT_CLASS_FILE);
    mxnet->device_type = g_strdup(DEFAULT_DEVICE_TYPE);
    mxnet->image_size = (int)DEFAULT_IMAGE_SIZE;
    mxnet->filter_tags = NULL;
    mxnet->imageProcessor = new ImageProcessor();
}

void gst_mxnet_set_property(GObject * object, guint property_id, const GValue * value, GParamSpec * pspec) {
    GstMXNet *mxnet = GST_MXNET (object);
    GST_DEBUG_OBJECT (mxnet, "set_property");

    switch (property_id) {
    case PROP_MODEL_FILE:
        g_free(mxnet->model_file);
        mxnet->model_file = g_strdup(g_value_get_string(value));
        mxnet->imageProcessor->setParam("model-file", std::string(mxnet->model_file));
        break;
    case PROP_CLASS_FILE:
        g_free(mxnet->klass_file);
        mxnet->klass_file = g_strdup(g_value_get_string(value));
        mxnet->imageProcessor->setParam("class-file", std::string(mxnet->klass_file));
        break;
    case PROP_DEVICE_TYPE:
        g_free(mxnet->device_type);
        mxnet->device_type = g_strdup(g_value_get_string(value));
        mxnet->imageProcessor->setParam("device-type", std::string(mxnet->device_type));
        break;
    case PROP_IMAGE_SIZE:
        mxnet->image_size = g_value_get_int(value);
        mxnet->imageProcessor->setParam("image-size", (int)(mxnet->image_size));
        break;
    case PROP_FILTER_TAGS: {
        const GstStructure *s = gst_value_get_structure(value);

        if (mxnet->filter_tags) {
            gst_structure_free(mxnet->filter_tags);
        }
        mxnet->filter_tags = s ? gst_structure_copy(s) : NULL;

        // Parse input configuration
        std::map<std::string, std::string> filter_tags;
        if (mxnet->filter_tags) {
            gboolean ret;
            ret = gstructToMap(mxnet->filter_tags, &filter_tags);
            if (!ret) {
                GST_WARNING("Failed to parse stream tags");
                break;
            }
        }
        mxnet->imageProcessor->setParams(filter_tags);
        break;
    }
    default:
        G_OBJECT_WARN_INVALID_PROPERTY_ID (object, property_id, pspec);
        break;
    }
}

void gst_mxnet_get_property(GObject * object, guint property_id, GValue * value, GParamSpec * pspec) {
    GstMXNet *mxnet = GST_MXNET (object);
    GST_DEBUG_OBJECT (mxnet, "get_property");

    switch (property_id) {
    case PROP_MODEL_FILE:
        g_value_set_string(value, mxnet->model_file);
        break;
    case PROP_CLASS_FILE:
        g_value_set_string(value, mxnet->klass_file);
        break;
    case PROP_DEVICE_TYPE:
        g_value_set_string(value, mxnet->device_type);
        break;
    case PROP_IMAGE_SIZE:
        g_value_set_int(value, mxnet->image_size);
        break;
    case PROP_FILTER_TAGS:
        gst_value_set_structure (value, mxnet->filter_tags);
        break;
    default:
        G_OBJECT_WARN_INVALID_PROPERTY_ID (object, property_id, pspec);
        break;
    }
}

void gst_mxnet_dispose(GObject * object) {
    GstMXNet *mxnet = GST_MXNET (object);

    GST_DEBUG_OBJECT (mxnet, "dispose");

    /* clean up as possible.  may be called multiple times */

    G_OBJECT_CLASS (gst_mxnet_parent_class)->dispose (object);
}

void gst_mxnet_finalize(GObject * object) {
    GstMXNet *mxnet = GST_MXNET (object);

    GST_DEBUG_OBJECT (mxnet, "finalize");

    /* clean up object here */
    if (mxnet->filter_tags) {
        gst_structure_free(mxnet->filter_tags);
    }

    if (mxnet->imageProcessor) {
        delete mxnet->imageProcessor;
    }

    G_OBJECT_CLASS (gst_mxnet_parent_class)->finalize (object);
}

static gboolean gst_mxnet_start(GstBaseTransform * trans) {
    GstMXNet *mxnet = GST_MXNET (trans);

    GST_DEBUG_OBJECT (mxnet, "start");

    return TRUE;
}

static gboolean gst_mxnet_stop(GstBaseTransform * trans) {
    GstMXNet *mxnet = GST_MXNET (trans);

    GST_DEBUG_OBJECT (mxnet, "stop");

    return TRUE;
}

static gboolean gst_mxnet_set_info(GstVideoFilter * filter, GstCaps * incaps,
    GstVideoInfo * in_info, GstCaps * outcaps, GstVideoInfo * out_info) {
    GstMXNet *mxnet = GST_MXNET (filter);

    mxnet->img_width = GST_VIDEO_INFO_WIDTH(in_info);
    mxnet->img_height = GST_VIDEO_INFO_HEIGHT(in_info);

    GST_DEBUG_OBJECT (mxnet, "set_info");

    return TRUE;
}

/* transform */
static GstFlowReturn gst_mxnet_transform_frame(GstVideoFilter * filter, GstVideoFrame * inframe,
    GstVideoFrame * outframe) {
    GstMXNet *mxnet = GST_MXNET (filter);

    GST_DEBUG_OBJECT (mxnet, "transform_frame");
    GST_DEBUG(">>>>> MXNET filter in action! <<<<<");

    // Process input frame
    cv::Mat img_src(mxnet->img_height, mxnet->img_width, CV_8UC3, inframe->data[0]);
    cv::Mat img_dst(mxnet->img_height, mxnet->img_width, CV_8UC3, outframe->data[0]);

    GstObjectsInfoArray *infoArray = mxnet->imageProcessor->process(img_src, img_dst);

    GstObjectsInfoMeta *meta = gst_buffer_add_objects_info_meta(outframe->buffer, infoArray);
    if (meta == NULL) {
        GST_LOG_OBJECT (mxnet, "Failed to attach metadata");
    }

    GstObjectsInfoArray* arr = gst_buffer_get_objects_info_meta(outframe->buffer);
    GST_LOG_OBJECT (mxnet, "Meta objects: %d", arr->size);

    // GST_LOG_OBJECT (mxnet, "Signaling from MXNET!!!");
    // g_signal_emit(G_OBJECT (mxnet), processing_complete_signal, 0, action);

    return GST_FLOW_OK;
}

static GstFlowReturn gst_mxnet_transform_frame_ip(GstVideoFilter * filter, GstVideoFrame * frame) {
    GstMXNet *mxnet = GST_MXNET (filter);

    GST_DEBUG_OBJECT (mxnet, "transform_frame_ip");

    return GST_FLOW_OK;
}

static gboolean plugin_init(GstPlugin * plugin) {
    /* FIXME Remember to set the rank if it's an element that is meant
      to be autoplugged by decodebin. */
    return gst_element_register (plugin, "mxnet", GST_RANK_NONE, GST_TYPE_MXNET);
}

/* FIXME: these are normally defined by the GStreamer build system.
   If you are creating an element to be included in gst-plugins-*,
   remove these, as they're always defined.  Otherwise, edit as
   appropriate for your external plugin package. */
#ifndef VERSION
#define VERSION "0.0.1"
#endif
#ifndef PACKAGE
#define PACKAGE "MXNET_package"
#endif
#ifndef PACKAGE_NAME
#define PACKAGE_NAME "MXNET_package_name"
#endif
#ifndef GST_PACKAGE_ORIGIN
#define GST_PACKAGE_ORIGIN "http://amazon.com/"
#endif

GST_PLUGIN_DEFINE (GST_VERSION_MAJOR,
    GST_VERSION_MINOR,
    mxnet,
    "MXNet inference plug-in",
    plugin_init, VERSION, "LGPL", PACKAGE_NAME, GST_PACKAGE_ORIGIN)
