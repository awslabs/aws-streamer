# Greengrass Setup

This greengrass group contains the following lambdas:

 - [GStreamer Pipeline](./gstreamer_pipeline/README.md)
 - [Data Uploader](./data_uploader/README.md)

## Group Settings

Make sure that greengrass groups have the following Group Role attached (in settings):

```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "kinesisvideo:*",
                "s3:*"
            ],
            "Resource": [
                "*"
            ]
        }
    ]
}
```

NOTE: this should be more constraint for secure deployment.

 ## Configuration

| Lambda name        | Type          | Lifecycle               | Memory (MB)     |
| ------------------ |:-------------:|:-----------------------:| ---------------:|
| gstreamer_pipeline | Python 3.7    | long-lived (aka pinned) | (1024 per camera) |
| data_uploader      | Python 3.7    | on-demand               | 1024            |

## Subscriptions

| From               | To                 | Topic             |
| ------------------ |:------------------:|:-----------------:|
| IoT Cloud          | gstreamer_pipeline | [group-id]/config/camera e.g. main-243/config/camera |
| IoT Cloud          | data_uploader      | [group-id]/req/data e.g. main-243/req/data |
| gstreamer_pipeline | IoT Cloud          | [group-id]/camera/feed e.g. main-243/camera/feed |
| data_uploader      | IoT Cloud          | [group-id]/data/res e.g. main-243/data/res |


## Resources

Inference Pipeline (*camera_inference*) lambda needs to have associated the following resources:

| Name              | Resource Type     | Local path            |
| ----------------- |:-----------------:|:---------------------:|
| video             | Volume            | /video        |


In addition to that, it should have attached Machine Learning resource pointing to the SageMaker model stored in S3.
Suggested local mapping is /model/ directory, which is referred by default. This path is referred later in stream
configuration under ml:model_dir.
