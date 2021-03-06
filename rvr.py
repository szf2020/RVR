# RVR demo with Intel Realsense 415 depth sensor


# First import the library
import pyrealsense2 as rs
import time
import sys
import os
import asyncio

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from sphero_sdk import SerialAsyncDal
from sphero_sdk import SpheroRvrAsync
from sphero_sdk.common.enums.drive_enums import DriveFlagsBitmask

# set the Realsense resolution to 848x480
yres = 480
xres = 848
ROIx1 = 0
ROIx2 = 848
ROIy1 = 220
ROIy2 = 280
yrange = ROIy2-ROIy1
xrange = ROIx2-ROIx1
xincrement = 5
binsize = 10
lastgood = 1 # this is the variable we use to pass over 0 depth pixels
bins = round(xrange/(binsize * xincrement)) # should be 13 bins in this case
epoch = 0
scan = [[],[]]
xstack = []
xbins = []
xbinsold = []
speed = 50 # Valid speed values are 0-255
heading = 0 # Valid heading values are 0-359
reverse = False
gain = 2.2


loop = asyncio.get_event_loop()
rvr = SpheroRvrAsync(
    dal=SerialAsyncDal(
        loop
    )
)

async def run_raw_motors(left_mode, left_speed, right_mode, right_speed):
    await rvr.raw_motors(left_mode, left_speed, right_mode, right_speed)

async def stop_raw_motors():
    await rvr.raw_motors(0, 0, 0, 0)

def setup():
    global scan, xstack, xbins, xbinsold
    print("rvr ready!")

    scan = [[0 for i in range(xres)] for j in range(yres)] # dimension the array
    flags=DriveFlagsBitmask.none.value
    for i in range(ROIx1,ROIx2): # set up an empty list of length xrange
        xstack.append(0)
    for i in range(bins): # set up an empty list of bin values for current and old values
        xbins.append(0)
        xbinsold.append(0)


async def main():

    global current_key_code, speed, heading, flags, reverse
    global epoch, xbinsold, ystack, xbins, xbinsold, scan, lastgood
    global ROIy1, ROIy2, yrange

    await rvr.wake()
    await rvr.reset_yaw()

    while True:
        frames = pipeline.wait_for_frames()
        depth = frames.get_depth_frame()
        if not depth: continue  # just do the loop again until depth returns true

        # Get the data
        for y in range(ROIy1,ROIy2):
            for x in range(ROIx1,ROIx2,xincrement):
                scan[y][x] = depth.get_distance(x, y)
                if scan[y][x] == 0:   # zero means bad data (too close/too far), if we get zero depth noise, just replace it with the last known good depth reading or a set number
                    scan[y][x] = lastgood
                else:
                    lastgood = 0.1  # in this case, we'll just call bad data "super close" and so we tend to steer away from it
#                    lastgood = scan[y][x]  # good data

        # Start averaging and binning:
        # First, average vertically
        for x in range(ROIx1,ROIx2,xincrement):
            xstack[x] = 0
            for y in range(ROIy1,ROIy2):  # sum up all the y's in each x stack
                xstack[x] = xstack[x] + scan[y][x]
            xstack[x] = round(xstack[x]/yrange,2)  # take average across the y's
            if 0 < xstack[x] <= 0.5:  # something is close
                print("X",end = '')
            elif 0.501 <= xstack[x] <= 1.0:
                print("x",end = '')
            elif 1.001 <= xstack[x] <= 1.5:
                print("-",end = '')
            elif 1.501 <= xstack[x] <= 2.0:
                print(".",end = '')
            elif xstack[x] > 2.001:
                print(" ",end = '')
            else:
                print("Something went wrong with my printing. X =", xstack[x])
        print("\n") # start a new line


        average = 0
        total = 0
        for i in range(bins-1):
            xbins[i] = 0
            for j in range(binsize):
                xbins[i] = xbins[i] + xstack[i*binsize*xincrement + j*xincrement]  # sum the bin
            xbins[i] = round(xbins[i]/binsize,2) # average the bin
            average = average + xbins[i]   # sum up all the x stacks
            total = total + 1
#         average = round(average/total,2)    # take the average of all the xstacks
# #        print("Average distance: ", average)

#       This next section is just if you want to use dynamic ROIs (looking further ahead if no obstacles are close)
#
        # # expand the ROI as necessary
        # if 0.0 <= average <= 0.25:
        #     ROIy1 = 220
        #     ROIy2 = 280
        #     yrange = ROIy2-ROIy1
        # elif 0.26 <= average <= 0.50:
        #     ROIy1 = 220
        #     ROIy2 = 280
        #     yrange = ROIy2-ROIy1
        # elif 0.51 <= average <= 0.75:
        #     ROIy1 = 220
        #     ROIy2 = 280
        #     yrange = ROIy2-ROIy1
        # elif 0.76 <= average <= 1.00:
        #     ROIy1 = 220
        #     ROIy2 = 280
        #     yrange = ROIy2-ROIy1
        # else:
        #     ROIy1 = 220
        #     ROIy2 = 280
        #     yrange = ROIy2-ROIy1


        # Now sum and average across each horizontal bin


        if (epoch != 0):
            for i in range(bins):
                xbins[i] = round((xbins[i]+xbinsold[i])/2,2)   # Bayesian smooothing
#            print("Xbins smoothed", xbins)
#            print("Longest range bin:", xbins.index(max(xbins)))
        xbinsold = list(xbins) # copy latest bins into oldbins for bayesian smoothing
        if epoch == 0:
            epoch = 1

        # make sure we're not stuck in a corner
        if (xbins[xbins.index(max(xbins))] < 0.75) and (xbins[xbins.index(max(xbins))] != 0):  # yikes, walls all around us!
            print("Longest range:", xbins[xbins.index(max(xbins))])
            # turn 15 degrees in the last direction you were going
            if heading > 180:
                heading = heading + 15
                await rvr.drive_with_heading(20, heading, flags)
            else:
                heading = heading - 15
                await rvr.drive_with_heading(20, heading, flags)
            await asyncio.sleep(0.1)
            print("let's try again..")
        else:
            # this is the driving part
            heading = heading + int(((xbins.index(max(xbins)) - (int(bins/2)+1))*gain))  # if higher than 6, steer to the right in 5 degree increments; if lower, drive left

            # check the speed value, and wrap as necessary.
            if speed > 255:
                speed = 255
            elif speed < -255:
                speed = -255

            # check the heading value, and wrap as necessary.
            if heading > 359:
                heading = heading - 359
            elif heading < 0:
                heading = 359 + heading

            flags = 0
            if reverse:
                flags = DriveFlagsBitmask.drive_reverse
            else:
                flags=DriveFlagsBitmask.none.value
            await rvr.drive_with_heading(speed, heading, flags)


setup()

try:
    # Create a pipeline
    pipeline = rs.pipeline()
    pipeline.start()

    # Create a config and configure the pipeline to stream
    #  different resolutions of color and depth streams
    config = rs.config()
    config.enable_stream(rs.stream.depth, xres, yres, rs.format.z16, 30)
    print("Starting...")
    loop.run_until_complete(
        main()
        )
except KeyboardInterrupt:
        print("Keyboard Interrupt...")
