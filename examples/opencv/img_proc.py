
import os
import awstreamer
import logging
import cv2

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def process(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return gray

if __name__ == '__main__':

    client = awstreamer.client()

    client.schedule({
        "test_display": {
            "enabled": True,
            "pipeline": "cv",
            "source": {
                "name": 0,
                "display": False
            },
            "process": process,
            "sink": {
                "pipeline": {
                    "pipeline": "appsrc",
                    "source": {
                        "width": 320,
                        "height": 320,
                        "fps": 30,
                        "img_format": "GRAY8"
                    },
                    "sink": {
                        "name": "autovideosink"
                    }
                },
                "display": True
            },
            "debug": True
        }
    }, wait_for_finish=True)

    print("All done.")
