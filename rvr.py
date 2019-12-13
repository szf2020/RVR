## License: Apache 2.0. See LICENSE file in root directory.
## Copyright(c) 2019 Intel Corporation. All Rights Reserved.

#####################################################
##                   Frame Queues                  ##
#####################################################

# First import the library
import pyrealsense2 as rs
import time
import sys
import os
import asyncio

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from sphero_sdk import SerialAsyncDal
from sphero_sdk import SpheroRvrAsync

loop = asyncio.get_event_loop()
rvr = SpheroRvrAsync(
    dal=SerialAsyncDal(
        loop
    )
)

async def main():
    global current_key_code
    global speed
    global heading
    global flags

    speed = 64
    heading = 10
    flags = 1

    await rvr.wake()

    await rvr.reset_yaw()
    # issue the driving command
    await rvr.drive_with_heading(speed, heading, flags)

    # sleep the infinite loop for a 10th of a second to avoid flooding the serial port.
    await asyncio.sleep(0.1)


# Implement two "processing" functions, each of which
# occassionally lags and takes longer to process a frame.
def slow_processing(frame):
    n = frame.get_frame_number()
    if n % 20 == 0:
        time.sleep(1/4)
    print(n)

def slower_processing(frame):
    n = frame.get_frame_number()
    if n % 20 == 0:
        time.sleep(1)
    print(n)

def run_loop():
    global loop
    loop.run_until_complete(
        asyncio.gather(
            main()
        )
    )
try:
    # Create a pipeline
    pipeline = rs.pipeline()

    # Create a config and configure the pipeline to stream
    #  different resolutions of color and depth streams
    config = rs.config()
    config.enable_stream(rs.stream.depth, 640, 360, rs.format.z16, 30)
    run_loop()
except KeyboardInterrupt:
        print("Keyboard Interrupt...")
        key_helper.end_get_key_continuous()
finally:
        print("Press any key to exit.")
        exit(1)
