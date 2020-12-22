
// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

#ifndef _GST_CVMLFILTER_H_
#define _GST_CVMLFILTER_H_

#include <gst/video/video.h>
#include <gst/video/gstvideofilter.h>

#include "ImageProcessor.h"

G_BEGIN_DECLS

#define GST_TYPE_CVMLFILTER   (gst_cvmlfilter_get_type())
#define GST_CVMLFILTER(obj)   (G_TYPE_CHECK_INSTANCE_CAST((obj),GST_TYPE_CVMLFILTER,GstCvmlFilter))
#define GST_CVMLFILTER_CLASS(klass)   (G_TYPE_CHECK_CLASS_CAST((klass),GST_TYPE_CVMLFILTER,GstCvmlFilterClass))
#define GST_IS_CVMLFILTER(obj)   (G_TYPE_CHECK_INSTANCE_TYPE((obj),GST_TYPE_CVMLFILTER))
#define GST_IS_CVMLFILTER_CLASS(obj)   (G_TYPE_CHECK_CLASS_TYPE((klass),GST_TYPE_CVMLFILTER))

typedef struct _GstCvmlFilter GstCvmlFilter;
typedef struct _GstCvmlFilterClass GstCvmlFilterClass;

struct _GstCvmlFilter {
    GstVideoFilter base_cvmlfilter;
    gint img_width;
    gint img_height;
    gchar *aws_region;
    GstStructure *filter_tags;
    ImageProcessor *imageProcessor;
};

struct _GstCvmlFilterClass {
    GstVideoFilterClass base_cvmlfilter_class;
};

GType gst_cvmlfilter_get_type(void);

G_END_DECLS

#endif
