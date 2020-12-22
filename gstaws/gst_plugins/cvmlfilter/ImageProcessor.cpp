
// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

#include <gst/gst.h>  // This is just for logging

#include <opencv2/core/core.hpp>
#include <opencv2/imgproc/imgproc.hpp>
#include <opencv2/core/utility.hpp>
#include <opencv2/dnn/dnn.hpp>
// #include <tensorflow/c/c_api.h>

#include "ImageProcessor.h"

#define CONFIG_CVML_MODEL_NAME       "cvml_model"
#define CONFIG_CVML_MODEL_PARAMS     "cvml_model_params"

ImageProcessor::ImageProcessor()
    :   cvNet(cv::dnn::Net()),
        default_action((PipelineAction)(PLAY_ALL)),
        threshold(50) {
    // Print available DNN backends
    std::vector<std::pair<cv::dnn::Backend, cv::dnn::Target> > backends = cv::dnn::getAvailableBackends();
    for (auto it = backends.begin(); it != backends.end(); ++it) {
        GST_INFO("DNN backend: %d --> %d", it->first, it->second);
    }
}

void ImageProcessor::setParams(const std::map<std::string, std::string> &params) {
    // Parse string to useful parameters
    if (!params.empty()) {
        for (auto it = params.begin(); it != params.end(); ++it) {
            GST_INFO("\t%s: %s", it->first.c_str(), it->second.c_str());
        }
    }

    // Load CVML model
    if (params.find(CONFIG_CVML_MODEL_NAME) != params.end() &&
        params.find(CONFIG_CVML_MODEL_PARAMS) != params.end()) {
        GST_INFO("CVML model loaded: %s", params.at(CONFIG_CVML_MODEL_NAME).c_str());
        cvNet = cv::dnn::readNetFromTensorflow(
            params.at(CONFIG_CVML_MODEL_NAME), params.at(CONFIG_CVML_MODEL_PARAMS));
    }

    // Face cascade
    if (params.find("face_cascade") != params.end()) {
        if (!face_cascade.load(params.at("face_cascade"))) {
            GST_ERROR("--(!)Error loading face cascade: %s\n", params.at("face_cascade").c_str());
        }
    }

    // Pipeline action
    if (params.find("pipeline_action") != params.end()) {
        default_action = (PipelineAction)std::stoi(params.at("pipeline_action"));
    }

    // Threshold
    if (params.find("threshold") != params.end()) {
        threshold = std::stoi(params.at("threshold"));
    }
}

PipelineAction ImageProcessor::process(const cv::Mat &src, cv::Mat &dst) {
    // Do your favourite image processing here, some examples:

    // Example #0: passthrough mode
    memcpy(dst.data, src.data, dst.total() * dst.elemSize());

    // Example #1: Distort image
    // distortImage(src, dst);

    // Example #2: Calculate average pixel value
    int result = calcAverage(src);

    // Example #3: Run neural network inference
    result += runNeuralNetworkInference(src, dst);

    // Example #4: Detect faces with cascades
    // int result = detectFaces(src, dst);

    // Set pipeline action based on processing result
    PipelineAction action = default_action;
    if (result == 0) {
        action = STOP_ALL;
    }
    return action;
}

void ImageProcessor::distortImage(const cv::Mat &src, cv::Mat &dst) {
    float w = src.cols;
    float h = src.rows;

    const cv::Point2f p_src[4]={
                cv::Point2f(0, 0),
                cv::Point2f(w, 0),
                cv::Point2f(w, h),
                cv::Point2f(0, h)};

    float offset_x = w / 8;

    const cv::Point2f p_dst[4]={
                cv::Point2f(0, 0),
                cv::Point2f(w, 0),
                cv::Point2f(w - offset_x, h),
                cv::Point2f(offset_x, h)};

    const cv::Mat mat_h = cv::getPerspectiveTransform(p_src, p_dst);
    cv::warpPerspective(src, dst, mat_h, src.size());
}

int ImageProcessor::calcAverage(const cv::Mat &src) {
    // Calculate average pixel value
    float w = src.cols;
    float h = src.rows;
    cv::Mat grayscale(h, w, CV_8UC1);
    cv::cvtColor(src, grayscale, cv::COLOR_BGR2GRAY);
    cv::Scalar avg = cv::mean(grayscale);
    GST_INFO("Average pixel value: %.1f", avg.val[0]);
    return avg.val[0] > threshold ? 1 : 0;
}

int ImageProcessor::runNeuralNetworkInference(const cv::Mat &src, cv::Mat &dst) {
    if (cvNet.empty()) {
        GST_WARNING("Neural network not initialized. Forgot to setup configuraton file?");
        return 0;
    }

    double t = (double)cv::getTickCount();
    float w = src.cols;
    float h = src.rows;
    bool swapRB = true;
    bool crop = false;

    // Run inference
    cvNet.setInput(cv::dnn::blobFromImage(src, 1.0, cv::Size(300, 300), cv::Scalar(104, 177, 123), swapRB, crop));
    cv::Mat detection = cvNet.forward();

    // Draw bounding boxes
    cv::Mat detectionMat(detection.size[2], detection.size[3], CV_32F, detection.ptr<float>());
    std::vector<std::vector<int>> bboxes;
    for (int i = 0; i < detectionMat.rows; i++) {
        float confidence = detectionMat.at<float>(i, 2);
        if (confidence > 0.5) {
            int x1 = static_cast<int>(detectionMat.at<float>(i, 3) * w);
            int y1 = static_cast<int>(detectionMat.at<float>(i, 4) * h);
            int x2 = static_cast<int>(detectionMat.at<float>(i, 5) * w);
            int y2 = static_cast<int>(detectionMat.at<float>(i, 6) * h);
            std::vector<int> box = {x1, y1, x2, y2};
            bboxes.push_back(box);
            cv::rectangle(dst, cv::Point(x1, y1), cv::Point(x2, y2), cv::Scalar(0, 255, 0),2, 4);
        }
    }

    t = ((double)cv::getTickCount() - t)/cv::getTickFrequency();
    GST_INFO("Inference took %.3f seconds", t);
    GST_INFO("Detected %lu bounding boxes", bboxes.size());

    return bboxes.size();
}

int ImageProcessor::detectFaces(const cv::Mat &src, cv::Mat &dst) {
    if (face_cascade.empty()) {
        GST_WARNING("Face cascade classifier not loaded. Forgot to setup configuraton file?");
        return 0;
    }

    int w = src.cols;
    int h = src.rows;
    cv::Mat grayscale(h, w, CV_8UC1);
    cv::cvtColor(src, grayscale, cv::COLOR_BGR2GRAY);
    cv::equalizeHist(grayscale, grayscale);

    //-- Detect faces
    std::vector<cv::Rect> faces;
    face_cascade.detectMultiScale(grayscale, faces);
    for (size_t i = 0; i < faces.size(); ++i) {
        cv::Point center( faces[i].x + faces[i].width/2, faces[i].y + faces[i].height/2 );
        cv::ellipse(dst, center, cv::Size( faces[i].width/2, faces[i].height/2 ), 0, 0, 360, cv::Scalar( 255, 0, 255 ), 4 );
    }
    return faces.size();
}