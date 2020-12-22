

#include <gst/gst.h>  // This is just for logging
#include "ImageProcessor.h"

/*
* Set this env variable to get logs from this file:
*   export GST_DEBUG=2,mxnet:8
*/
GST_DEBUG_CATEGORY_STATIC (mxnet_infer);
#define GST_CAT_DEFAULT mxnet_infer

ImageProcessor::ImageProcessor()
    :   ctx(Context::cpu()),
        exec(NULL) {
    // Initialize logger
    GST_DEBUG_CATEGORY_INIT(mxnet_infer, "mxnet_infer", 0, "MXNet::ImageProcessor() construction done");
}

void ImageProcessor::setParam(const std::string &key, std::any val) {
    if (key == "model-file") {
        this->model_file = std::any_cast<std::string>(val);
        GST_INFO("Loading model: %s", this->model_file.c_str());
        LoadCheckpoint(this->model_file, epoch, &net, &args, &auxs, ctx);
    } else if (key == "class-file") {
        this->class_file = std::any_cast<std::string>(val);
        GST_INFO("Class file: %s", this->class_file.c_str());
        this->class_names = LoadClassNames(this->class_file);
    } else if (key == "device-type") {
        this->device_type = std::any_cast<std::string>(val);
        GST_INFO("Device type: %s", this->device_type.c_str());
        if (this->device_type == "gpu") {
            // Parse GPU index from the name
            ctx = Context::gpu(gpu);
        }
    } else if (key == "image-size") {
        this->image_size = std::any_cast<int>(val);
        GST_INFO("Image size: %d", this->image_size);
        min_size = this->image_size;
        max_size = this->image_size;
    }
}

void ImageProcessor::setParams(const std::map<std::string, std::string> &params) {
    // Parse string to useful parameters
    if (!params.empty()) {
        for (auto it = params.begin(); it != params.end(); ++it) {
            GST_INFO("\t%s: %s", it->first.c_str(), it->second.c_str());
        }
    }
}

GstObjectsInfoArray* ImageProcessor::process(const cv::Mat &src, cv::Mat &dst) {
    // Copy src to dst
    memcpy(dst.data, src.data, dst.total() * dst.elemSize());

    // // Resize image
    // cv::resize(dst, dst, cv::Size(min_size, min_size));

    // Resize again
    cv::Mat image = ResizeShortWithin(dst, min_size, max_size, multiplier);
    GST_INFO("\tImage shape: %d x %d", image.cols, image.rows);

    // Set input and bind executor
    auto data = AsData(image, ctx);
    if (exec == NULL) {
        args["data"] = data;
        exec = net.SimpleBind(
            ctx, args, std::map<std::string, NDArray>(),
            std::map<std::string, OpReqType>(), auxs);
    } else {
        data.CopyTo(&args["data"]);
    }

    // Begin forward
    NDArray::WaitAll();
    auto start = std::chrono::steady_clock::now();
    exec->Forward(false);
    auto ids = exec->outputs[0].Copy(Context(kCPU, 0));
    auto scores = exec->outputs[1].Copy(Context(kCPU, 0));
    auto bboxes = exec->outputs[2].Copy(Context(kCPU, 0));
    NDArray::WaitAll();
    auto end = std::chrono::steady_clock::now();
    GST_INFO("\tElapsed time {Forward->Result}: %.4f ms", std::chrono::duration<double, std::milli>(end - start).count());

    // // Draw boxes
    // auto plt = viz::PlotBbox(image, bboxes, scores, ids, viz_thresh, class_names, std::map<int, cv::Scalar>(), true);
    // GST_INFO("\tOutput image shape: %d x %d", plt.cols, plt.rows);
    // cv::resize(plt, dst, cv::Size(src.cols, src.rows));

    // Put results to the metadata
    float thresh = 0.0;
    int num = bboxes.GetShape()[1];
    std::mt19937 eng;
    std::uniform_real_distribution<float> rng(0, 1);
    bboxes.WaitToRead();
    scores.WaitToRead();
    ids.WaitToRead();

    std::vector<GstObjectInfo> infoVec;
    for (int i = 0; i < num; ++i) {
        float score = scores.At(0, 0, i);
        float id = ids.At(0, 0, i);
        if (score < thresh || id < 0) {
            continue;
        }

        GstObjectInfo info;
        info.x = bboxes.At(0, i, 0);
        info.y = bboxes.At(0, i, 1);
        info.width = bboxes.At(0, i, 2);
        info.height = bboxes.At(0, i, 3);
        info.confidence = score;

        int cls_id = static_cast<int>(id);
        if (cls_id >= (int)(class_names.size())) {
            GST_INFO("\tid: %d, scores: %.4f", cls_id, score);
            info.class_name = g_strdup("Unknown");
        } else {
            GST_INFO("\tid: %s, scores: %.4f", class_names[cls_id].c_str(), score);
            info.class_name = g_strdup(class_names[cls_id].c_str());
        }
        info.track_id = cls_id;
        infoVec.push_back(info);
    }

    // Copy to C-array
    GstObjectsInfoArray *infoArray = (GstObjectsInfoArray*)malloc(sizeof(GstObjectsInfoArray));
    if (infoVec.size() > 0) {
        infoArray->items = (GstObjectInfo*)malloc(sizeof(GstObjectInfo) * infoVec.size());
        std::copy(infoVec.begin(), infoVec.end(), infoArray->items);
        infoArray->size = infoVec.size();
    }
    return infoArray;
}
