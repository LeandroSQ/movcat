#!/usr/bin/env python

import os
import cv2
import argparse
import fcntl
import termios
import struct
import time
import pybase64
import sys

#region Terminal utilities
def write(msg):
    sys.stdout.write(msg)

def clearTerminal():
    write("\033]50;ClearScrollback\007")
    # write("\033[H\033[3J")

def setTerminalTitle(title):
    # Set terminal title
    write("\033]0;" + title + "\007")

def getTerminalSizeInPixels(paddingX=0, paddingY=0):
    # Get terminal size
    buf = fcntl.ioctl(1, termios.TIOCGWINSZ, struct.pack("HHHH", 0, 0, 0, 0))
    _, _, width_pixels, height_pixels = struct.unpack("HHHH", buf)

    return width_pixels - paddingX, height_pixels - paddingY

def printImageData(data):
    # https://iterm2.com/documentation-images.html
    write(f"\033[0;0H\033]1337;File=size={str(len(data))};inline=1:{data}\a")
#endregion

#region Video utilities
def calculateFrameSize(cap):
    # Get the terminal window size, in pixels
    width, height = getTerminalSizeInPixels(paddingX=1, paddingY=1)
    # print("Terminal size: " + str(width) + "x" + str(height))

    # Get frame aspect ratio
    aspectRatio = extractFrameAspectRatio(cap)
    # print("Frame aspect ratio: " + str(aspectRatio))

    # Calculate frame size, based on terminal window size and frame aspect ratio
    frameWidth = width
    frameHeight = int(frameWidth / aspectRatio)
    # print("Frame size: " + str(frameWidth) + "x" + str(frameHeight))

    return frameWidth, frameHeight

def extractFrameAspectRatio(cap):
    # Get frame width and height
    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)

    # Calculate aspect ratio
    aspectRatio = width / height

    return aspectRatio

def setupVideoCaptureInterface(filename):
    # Initialize video capture
    cap = cv2.VideoCapture(filename)
    if not cap.isOpened():
        print("Error opening video stream or file")
        error = cap.get(cv2.CAP_PROP_POS_MSEC)
        print("Error at: " + str(error))
        return None

    return cap
#endregion

#region Misc
def getHighResolutionTimestamp():
    return time.time_ns() / 1000000

def encodeImageToBase64(bytes):
    return pybase64.b64encode(bytes).decode('ascii')

def prettifyFilename(filename):
    name = os.path.basename(filename)
    if len(name) > 20:
        name = name[:20] + "..."
    return name
#endregion

def loop(filename):
    # Initialize video capture
    cap = setupVideoCaptureInterface(filename)
    if not cap: return sys.exit(1)

    # Calculate frame size
    width, height = calculateFrameSize(cap)

    # Variables
    targetFPS = cap.get(cv2.CAP_PROP_FPS)
    cap.set(cv2.CAP_PROP_POS_FRAMES, 4250)
    lastFrameTime = None
    currentFrameTime = None
    frameInterval = 1000 / targetFPS
    frameCount = 0
    terminalClearInterval = targetFPS * 5 # In seconds
    terminalClearFrameCounter = 0
    fpsTimer = time.time()

    # Pre-allocate memory for frame
    frame = None
    success = False
    buffer = None
    while cap.isOpened():
        try:
            # Store the time for the frame start
            lastFrameTime = getHighResolutionTimestamp()

            # Fetch frame from video capture
            success, frame = cap.read()
            if not success:
                print("Error reading frame!")
                print(f"Error at: {str(cap.get(cv2.CAP_PROP_POS_MSEC))}")
                break

            # Resize frame to terminal window size, to avoid distortion and improve performance
            frame = cv2.resize(frame, (width, height))

            # Encode it to a .jpg file format, save it to memory buffer
            success, buffer = cv2.imencode('.jpg', frame)
            if not success:
                print("Error encoding frame!")
                break

            # Encode image bytes to base64
            buffer = encodeImageToBase64(buffer.tobytes())

            # Clear terminal every X seconds
            terminalClearFrameCounter += 1
            if terminalClearFrameCounter > terminalClearInterval:
                terminalClearFrameCounter = 0
                clearTerminal()

            # Print frame on terminal
            printImageData(buffer)

            # Ensure the frame rate is respected
            currentFrameTime = getHighResolutionTimestamp()
            frameTime = currentFrameTime - lastFrameTime
            if frameTime < frameInterval:
                time.sleep((frameInterval - frameTime) / 1000)

            # Calculate FPS
            frameCount += 1
            if time.time() - fpsTimer >= 1.0:
                fpsTimer += 1.0
                setTerminalTitle(f"MovCat - {prettifyFilename(filename)} - FPS: {frameCount}")
                frameCount = 0
        except Exception as e:
            print("Error on main loop!")
            print(e)
            break

    # Release video capture
    cap.release()

def main():
    # Define CLI arguments
    parser = argparse.ArgumentParser(
        prog="MovCat",
        description="Given a video file, print it on the terminal using iTerm2 inline image protocol.",
        epilog="Example: python3 main.py test.mp4"
    )
    parser.add_argument("filename", help="Path to video file to be printed on terminal", type=str)
    args = parser.parse_args()

    # Validate CLI arguments
    if not args.filename:
        print("Filename not specified")
        return sys.exit(1)

    if not os.path.exists(args.filename):
        print("File does not exist")
        return sys.exit(1)

    # Clear terminal
    clearTerminal()

    args.filename = "/Volumes/Media/Movies/Hercules.1997.1080p.BluRay.5.1.x264.DUAL-WWW.BLUDV.COM.mkv"

    # Set terminal title
    setTerminalTitle(f"MovCat - {prettifyFilename(args.filename)}")

    loop(args.filename)

if __name__ == "__main__":
    main()