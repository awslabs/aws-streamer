
import os
import gstaws
from pprint import pformat

dir_path = os.path.abspath(os.path.dirname(__file__))

def my_callback(metadata):
    '''
    This function will be called on every frame containing inference results
    '''
    print("Inference result: " + str(pformat(metadata)))

if __name__ == '__main__':

    # Initialize gstaws client
    client = gstaws.client()

    # Start a new pipeline synchronously
    client.start({
        "pipeline": "DeepStream",
        "source": {
            "name": "filesrc",
            "location": "/opt/nvidia/deepstream/deepstream/samples/streams/sample_720p.mp4",
            "do-timestamp": False
        },
        "sink": {
            "name": "autovideosink"
        },
        "nvstreammux": {
            "width": 1280,
            "height": 720,
            "batch-size": 1
        },
        "nvinfer": {
            "enabled": True,
            "config-file-path": os.path.join(dir_path, "nvinfer_config.txt")
        },
        "callback": my_callback
    })

    print("All done.")
