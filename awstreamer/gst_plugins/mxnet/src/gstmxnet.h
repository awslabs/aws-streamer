
#ifndef _GST_MXNET_H_
#define _GST_MXNET_H_

#include <gst/video/video.h>
#include <gst/video/gstvideofilter.h>

#include "ImageProcessor.h"

G_BEGIN_DECLS

#define GST_TYPE_MXNET   (gst_mxnet_get_type())
#define GST_MXNET(obj)   (G_TYPE_CHECK_INSTANCE_CAST((obj),GST_TYPE_MXNET,GstMXNet))
#define GST_MXNET_CLASS(klass)   (G_TYPE_CHECK_CLASS_CAST((klass),GST_TYPE_MXNET,GstMXNetClass))
#define GST_IS_MXNET(obj)   (G_TYPE_CHECK_INSTANCE_TYPE((obj),GST_TYPE_MXNET))
#define GST_IS_MXNET_CLASS(obj)   (G_TYPE_CHECK_CLASS_TYPE((klass),GST_TYPE_MXNET))

typedef struct _GstMXNet GstMXNet;
typedef struct _GstMXNetClass GstMXNetClass;

struct _GstMXNet {
    GstVideoFilter base_mxnet;
    gint img_width;
    gint img_height;
    gchar *model_file;
    gchar *klass_file;
    gchar *device_type;
    gint image_size;
    GstStructure *filter_tags;
    ImageProcessor *imageProcessor;
};

struct _GstMXNetClass {
    GstVideoFilterClass base_mxnet_class;
};

GType gst_mxnet_get_type(void);

G_END_DECLS

#endif
