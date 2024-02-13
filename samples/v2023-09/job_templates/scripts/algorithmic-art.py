# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#

import numpy as np
from PIL import Image
from pathlib import Path
import sys
import re

def polar_2d(dimensions: tuple[int,int]) -> tuple[np.ndarray, np.ndarray]:
    # 2d arrays of polar coordinates (r,theta) with the center of the polar plane
    # at the dimensional center of the returned grid.
    # Input: dimensions -- (width,height)
    # Returns: (radius, theta)
    # Each y[i] is an array w/ values 0..dimensions[0]
    # Each x[i] is an array of length x filled with i's
    x,y = np.meshgrid(*map(range, dimensions))
    center = np.array(dimensions)/2
    x,y = x-center[0], y-center[1]
    radius = np.sqrt(x**2 + y**2)
    theta = np.arctan2(y,x)
    return radius, theta

def false_color_map() -> np.ndarray:
    # Generate a falsecolor map
    # Return: uint8[256][3]
    colors = np.array([[0,255,0],[255,255,0],[255,0,0],[255,0,255],[0,0,255],[0,255,255],[0,255,0]])
    positions = [0,30,90,120,190,230,255]
    assert len(positions) == len(colors)
    colormap = np.zeros((256,3), dtype=np.uint8)
    for idx in range(0, len(colors)-1):
        c1,c2,p1,p2 = colors[idx],colors[idx+1],positions[idx],positions[idx+1]
        # Linear interpolation between the colors
        for i in range(p1,p2+1):
            x = (i-p1)/(p2-p1)
            colormap[i,:] = c1*(1-x)+c2*x
    return colormap

def apply_color_map(image: np.ndarray, colors: np.ndarray) -> np.ndarray:
    flattened = np.uint8(image.reshape(-1))
    return colors[flattened].reshape(image.shape+(3,))

def generate_image(dimensions: tuple[int,int], jaggy: float, star: int, swirl: float) -> Image:
    # Note: Fractional 'star' leads to discontinuities in the image.
    radius,theta = polar_2d(dimensions)
    log_radius = np.log(1+radius)
    np_image = np.sin(theta*star + np.sin(log_radius*jaggy) + log_radius*swirl)
    # Vary the color with distance from the center
    np_image += log_radius
    # Clamp to [0,1] and apply the false coloring
    clamped_image = np.fmod(np_image, 1)
    color_map = false_color_map()
    raw_data = apply_color_map(255*clamped_image, color_map)
    return Image.fromarray(raw_data)

def usage():
    print(f"Usage: {sys.argv[0]} <output directory: str> '<frame:int> of <maxframes:int>' <star_factor: float> <swirl_factor:float>")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        usage()
        sys.exit(1)
    if not (frame_info := re.match("(.+) of (.+)", sys.argv[2])):
        print("Error - Frame argument malformed")
        usage()
        sys.exit(1)
    try:
        frame = int(frame_info[1])
        max_frame = int(frame_info[2])
        star_factor = int(sys.argv[3])
        swirl_factor = float(sys.argv[4])
    except:
        print("Error parsing arguments")
        usage()
        sys.exit(1)

    frame_ratio = frame/max_frame
    # Linearly interpolate
    jaggy = 1*(1-frame_ratio) + 5*frame_ratio

    image = generate_image((640,480), jaggy, star_factor, swirl_factor)
    outfile_name = str(Path(sys.argv[1]) / f"algart-{star_factor}-{swirl_factor}-{str(frame).zfill(4)}.png")
    print("Writing image: ", outfile_name)
    image.save(outfile_name)
