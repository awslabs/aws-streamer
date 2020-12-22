#ifndef __IMAGE_PROCESSOR_H__
#define __IMAGE_PROCESSOR_H__

#include <vector>
#include <map>
#include <any>
#include <chrono>
#include <opencv2/core/core.hpp>
#include <gst_objects_info_meta.h>
#include "common.hpp"

class ImageProcessor {
  public:
    ImageProcessor();
    void setParams(
        const char *model_file,
        const char *klass_file,
        const char *device_type,
        unsigned int image_size
    );
    void setParam(const std::string &key, std::any val);
    void setParams(const std::map<std::string, std::string> &params);
    GstObjectsInfoArray* process(const cv::Mat &img_src, cv::Mat &img_dst);

  private:

    Symbol net;
    Context ctx;
    Executor *exec;

    std::map<std::string, NDArray> args, auxs;
    std::string model_file;
    std::string device_type;
    std::string output;
    std::string class_file;
    std::vector<std::string> class_names;
    int epoch = 0;
    int gpu = -1;
    bool quite = false;
    bool no_display = false;
    float viz_thresh = 0.3;
    int image_size = 512;
    int min_size = 512;
    int max_size = 640;
    int multiplier = 32;  // just to ensure image shapes are multipliers of feature strides, for yolo3 models
};

#endif // __IMAGE_PROCESSOR_H__
