// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

#ifndef __IMAGE_PROCESSOR_H__
#define __IMAGE_PROCESSOR_H__

#include <vector>
#include <map>
#include <opencv2/dnn/dnn.hpp>
#include "opencv2/objdetect.hpp"

enum PipelineAction {
    STOP_ALL                = 0,
    SIMPLE_PIPE_PLAY        = (1u << 0),
    CVML_PIPE_PLAY          = (1u << 1),
    PLAY_ALL                = SIMPLE_PIPE_PLAY | CVML_PIPE_PLAY
};

class ImageProcessor {
  public:
    ImageProcessor();
    void setParams(const std::map<std::string, std::string> &params);
    PipelineAction process(const cv::Mat &img_src, cv::Mat &img_dst);

  private:
    void distortImage(const cv::Mat &src, cv::Mat &dst);
    int calcAverage(const cv::Mat &src);
    int runNeuralNetworkInference(const cv::Mat &src, cv::Mat &dst);
    int detectFaces(const cv::Mat &src, cv::Mat &dst);

    cv::dnn::Net cvNet;
    PipelineAction default_action;
    int threshold;
    cv::CascadeClassifier face_cascade;
};

#endif // __IMAGE_PROCESSOR_H__
