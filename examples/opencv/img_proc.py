
import os
import awstreamer
import logging
import cv2

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

if __name__ == '__main__':

    # Start an appsrc pipeline asynchronously
    client = awstreamer.client()
    pipeline, thread = client.start({
        "pipeline": "appsrc",
        "source": {
            "width": 320,
            "height": 320,
            "fps": 30
        },
        "sink": {
            "name": "hlssink",
            "location": "/video/segment%05d.ts",
            "playlist-location": "/video/playlist.m3u8",
            "max-files": 5
        }
    }, wait_for_finish=False)

    # Video source
    source = cv2.VideoCapture(0)

    while True:
        # Capture frame
        ret, img = source.read()
        if not ret:
            logger.error("Can't receive frame (stream end?). Exiting ...")
            break

        # Push to appsrc
        img = cv2.resize(img, (320,320))
        pipeline.push(img)

        # Display
        cv2.imshow("output", img)
        cv2.waitKey(1)

    thread.join()
    print("All done.")
