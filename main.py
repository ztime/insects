import os
import sys
import numpy as np
import random
import argparse
import pickle
import subprocess
import tempfile
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from pprint import pprint

from bug_math import VelocityField, precalculate_values, generate_perlin_noise_3d, generate_random_noise_3d

class Insect:
    def __init__(self, startpos, bound_x, bound_y, bound_z, name):
        self.name = name
        x,y,z = startpos
        x = float(x)
        y = float(y)
        z = float(z)
        self.position = (x,y,z)
        self.bound_x = float(bound_x)
        self.bound_y = float(bound_y)
        self.bound_z = float(bound_z)

    def move(self, move_vector):
        current_x, current_y, current_z = self.position
        move_x, move_y, move_z = move_vector
        new_x = current_x + move_x
        new_y = current_y + move_y
        new_z = current_z + move_z
        # Testing with removing this check
        if new_x < 0.0 or new_x > self.bound_x - 1.0:
            new_x = current_x - move_x
        if new_y < 0.0 or new_y > self.bound_y - 1.0:
            new_y = current_y - move_y
        if new_z < 0.0 or new_z > self.bound_z - 1.0:
            new_z = current_z - move_z
        self.position = (new_x, new_y, new_z)

    def get_rounded_position(self):
        x,y,z = self.position
        return (int(x), int(y), int(z))

    def __str__(self):
        x,y,z = self.position
        return f"Bug {self.name}: {x:.2f}, {y:.2f}, {z:.2f}"

def main():
    # argparse
    parser = argparse.ArgumentParser(description='Generate some insects flying infront of the camera')
    parser.add_argument('-o', '--output', type=os.path.abspath, help='filename (without extenstion) for the finished .avi file')
    parser.add_argument('--frames', type=int, default=150, help='How many frames to generate')
    parser.add_argument('--framerate', type=int, default=25, help='What framerate to generate the video with')
    parser.add_argument('--save_images', action='store_true', help='If true, images are saved to a permanent folder, otherwise tempfolder is used')
    parser.add_argument('--save_images_path', type=os.path.abspath, help='Where to save the images')
    parser.add_argument('--bugs', type=int, default=10, help='How many bugs to render')
    parser.add_argument('--dimX', type=int, default=128, help='Define dimension of the X axis')
    parser.add_argument('--dimY', type=int, default=128, help='Define dimension of the Y axis')
    parser.add_argument('--dimZ', type=int, default=128, help='Define dimension of the Z axis')
    parser.add_argument('--perlin_load_path', type=os.path.abspath, help='Folder to look for saved perlin files')
    parser.add_argument('--perlin_save_path', type=os.path.abspath, help='Folder to save perlin files in')
    parser.add_argument('--one_frame', action='store_true', help='Shows one frame and then quits - for debugging')
    parser.add_argument('--angle', type=int, default=40, help='Passed to pyplot')
    parser.add_argument('--elevation', type=int, default=6, help='Passed to pyplot')
    parser.add_argument('--zoom', help='Pyplot zoom - define start-end on axis as ints (ex --zoom 130-170). Check what you want with --show_debug_grid and --one_frame')
    parser.add_argument('--show_debug_grid', action='store_true', help='Show the axis and plot dimensions')
    parser.add_argument('--plot_vec_field', action='store_true', help='Plots the vector field of the last Perlin field constructed, then quits - for debugging')
    parser.add_argument('--debug_repl', action='store_true', help='Loads a repl for the last Perlin field constructed, then quits - for debugging')
    parser.add_argument('--plot_alpha', action='store_true', help='Plot the alpha function from vector field, then quits')
    parser.add_argument('--yes_to_all', action='store_true', help='Dont stop to ask questions, just go. !! Will overwrite things !!')
    parser.add_argument('--append_params_to_name', action='store_true', help='Put a bunch of parameters in the name of the file, to keep track of how it was generated')
    parser.add_argument('--number_perlin_fields', type=int, default=1, help='How many perlin fields to use')
    parser.add_argument('--switch_fields_every_frame', type=int, default=10, help='Every x frame switch perlin field to the next one')
    args = parser.parse_args()

    no_frames = args.frames
    bound_x = args.dimX
    bound_y = args.dimY
    bound_z = args.dimZ

    # Create several v_f for use
    # The last one created is the one for which we use the settings
    vector_fields = []
    for i in range(args.number_perlin_fields):
        p_x, p_y, p_z = perlin_values((bound_x, bound_y, bound_z), args.perlin_load_path, args.perlin_save_path, args.yes_to_all, field_index=i)
        v_f = VelocityField(p_x, p_y, p_z, bound_x, bound_y, bound_z)
        vector_fields.append(v_f)

    if args.debug_repl:
        v_f.debug_repl()
    if args.plot_alpha:
        v_f.plot_alpha_ramp()
    if args.plot_vec_field:
        v_f.plot_vec_field(step_size=32)

    no_bugs = args.bugs
    bugs = []
    for i in range(no_bugs):
        x = random.randint(0,bound_x - 1)
        y = random.randint(0,bound_y - 1)
        z = random.randint(0,bound_z - 1)
        bugs.append(Insect((float(x),float(y),float(z)), float(bound_x), float(bound_y), float(bound_z), f"{i}"))

    if args.save_images:
        save_images_folder = args.save_images_path
    else:
        save_images_folder_obj = tempfile.TemporaryDirectory()
        save_images_folder = save_images_folder_obj.name
    if not os.path.isdir(save_images_folder):
        os.mkdir(save_images_folder)

    no_of_numbers = len(str(no_frames))
    frame_counter = 0
    # Keep track of and change fields
    vector_field_index = 0
    for frame in range(no_frames):
        frame = np.zeros((bound_x,bound_y,bound_z))
        print("Moving bugs...", end='')
        for bug in bugs:
            # Print buggy
            x,y,z = bug.get_rounded_position()
            frame[x, y, z] = 1
            # Move buggy
            move_x, move_y, move_z = vector_fields[vector_field_index].get_velocity(bug.get_rounded_position())
            bug.move((move_x, move_y, move_z))
        print("Generating frame...", end='')
        x_vals, y_vals, z_vals = positions_from_grid(frame)
        filename = f"{save_images_folder}/bugs-frame-{frame_counter:0>{no_of_numbers}}.png"
        if args.one_frame:
            show_image_from_grid(
                    x_vals,
                    y_vals,
                    z_vals,
                    filename=filename,
                    elevation=args.elevation,
                    xy_angle=args.angle,
                    zoom=args.zoom,
                    show_debug_grid=args.show_debug_grid,
                    )
            quit()
        save_image_from_grid(
                x_vals,
                y_vals,
                z_vals,
                filename=filename,
                elevation=args.elevation,
                xy_angle=args.angle,
                zoom=args.zoom,
                show_debug_grid=args.show_debug_grid,
                )
        print(f"Saved frame {frame_counter} as {filename}!\r", end='')
        # frame is done!
        frame_counter += 1
        # Lets see if we want to switch fields
        if frame_counter % args.switch_fields_every_frame == 0:
            vector_field_index += 1
            vector_field_index = vector_field_index % args.number_perlin_fields
    if args.append_params_to_name:
        extra_params = f"-bugs-{no_bugs}-dim-{args.dimX}x{args.dimY}x{args.dimZ}-fields-{args.number_perlin_fields}-d_0-{v_f.D_0}-P_GAIN-{v_f.P_GAIN}"
        args.output = f"{args.output}{extra_params}.avi"
    save_video_from_grid(save_images_folder, args.framerate, args.output)

    if not args.save_images:
        print(f"Cleaning up temporary folder {save_images_folder}...")
        save_images_folder_obj.cleanup()
        print("Cleanup done.")
    print(f"{args.output}")

def save_video_from_grid(frames_folder, framerate, video_filename):
    # generate video
    print("Using ffmpeg to generate avi video...")
    commands = [
            'ffmpeg',
            '-y', # Overwrite files without asking
            '-r', # Set framerate...
            f"{framerate}", # ...to seq_length
            '-pattern_type', # Regextype ...
            'glob', # ...set to global
            f"-i", # Pattern to use when ...
            f"'{frames_folder}/*.png'", # ...looking for image files
            '-s', # Set size
            '128x128', #
            f"{video_filename}", # Where to save
            ]
    print(f"Running command '{' '.join(commands)}'")
    subprocess.run(' '.join(commands), shell=True)
    print("Done generating video!")

def save_perlin_noise(folder, filename, p, dimension, index=0):
    if not os.path.isdir(folder):
        os.mkdir(folder)
    with open(perlin_filename(folder,filename,dimension,index), 'wb') as f:
        pickle.dump(p, f)

def load_perlin_noise(folder, filename, dimension, index=0):
    loaded_p = None
    try:
        with open(perlin_filename(folder,filename,dimension,index), 'rb') as f:
            loaded_p = pickle.load(f)
        return loaded_p
    except OSError:
        # We couldnt find it
        return None

def perlin_filename(folder,filename,dimension,index):
    if index == 0:
        return f'{folder}/{filename}_{dimension}.perlin'
    else:
        return f'{folder}/{filename}_{dimension}_{index}.perlin'

def perlin_values(bounds, load_path, save_path, yes_to_all, field_index=0):
    # Define defaults
    # Resolution for perlin noise.. maybe
    res = (8,8,8)
    b_x, b_y, b_z = bounds
    p_x = None
    p_y = None
    p_z = None
    # Check if files has been loaded
    loaded_p_x = False
    loaded_p_y = False
    loaded_p_z = False
    # Lets see if we can load any!
    if load_path is not None:
        print("Trying to load p_x...")
        l_p_x = load_perlin_noise(load_path, 'p_x', b_x,index=field_index)
        if l_p_x is None:
            print(f"Could not load p_x for {b_x}, creating...")
            l_p_x = generate_perlin_noise_3d(bounds,res)
            # l_p_x = generate_random_noise_3d(bounds,res)
            print("Done")
        else:
            print("Successful loading of p_x!")
            loaded_p_x = True
        p_x = l_p_x

        print("Trying to load p_y...")
        l_p_y = load_perlin_noise(load_path, 'p_y', b_y,index=field_index)
        if l_p_y is None:
            print(f"Could not load p_y for {b_y}, creating...")
            l_p_y = generate_perlin_noise_3d(bounds,res)
            # l_p_y = generate_random_noise_3d(bounds,res)
            print("Done")
        else:
            print("Successful loading of p_y!")
            loaded_p_y = True
        p_y = l_p_y

        print("Trying to load p_z...")
        l_p_z = load_perlin_noise(load_path, 'p_z', b_z,index=field_index)
        if l_p_z is None:
            print(f"Could not load p_z for {b_z},creating...")
            l_p_z = generate_perlin_noise_3d(bounds,res)
            # l_p_z = generate_random_noise_3d(bounds,res)
            print("Done")
        else:
            print("Successful loading of p_z!")
            loaded_p_z = True
        p_z = l_p_z
    else:
        # We have to create p_x, p_y, p_z because they
        # dont exist yet
        print(f"Creating new fields!")
        p_x = generate_perlin_noise_3d(bounds,res)
        print(f"p_x - {field_index} done...")
        p_y = generate_perlin_noise_3d(bounds,res)
        print(f"p_y - {field_index} done...")
        p_z = generate_perlin_noise_3d(bounds,res)
        print(f"p_z - {field_index} done!")
    # now we know that p_[x,y,z] are filled with values
    # Lets see if we wanna save it
    if save_path is not None:
        if loaded_p_x:
            print("p_x was loaded, skipping save...")
        else:
            print("Saving p_x...")
            save_perlin_noise(save_path, 'p_x', p_x, b_x,index=field_index)
            print("Saved!")
        if loaded_p_y:
            print("p_y was loaded, skipping save...")
        else:
            print("Saving p_y...")
            save_perlin_noise(save_path, 'p_y', p_y, b_y,index=field_index)
            print("Saved!")
        if loaded_p_z:
            print("p_z was loaded, skipping save...")
        else:
            print("Saving p_z...")
            save_perlin_noise(save_path, 'p_z', p_z, b_z,index=field_index)
            print("Saved!")

    return p_x, p_y, p_z

def generate_image(x_vals, y_vals, z_vals, elevation, xy_angle, zoom, show_debug_grid):
    side_size = 6.4
    fig = plt.figure(figsize=(side_size, side_size))
    ax = fig.add_subplot(111, projection='3d')
    if zoom is not None:
        lower = int(zoom.split('-')[0])
        upper = int(zoom.split('-')[1])
        ax.set_xlim(lower,upper)
        ax.set_ylim(lower,upper)
        ax.set_zlim(lower,upper)

    if show_debug_grid:
        ax.scatter(x_vals, y_vals, z_vals, depthshade=True)
    else:
        ax.scatter(x_vals, y_vals, z_vals, c='white', depthshade=False)
    ax.view_init(elev=elevation, azim=xy_angle)
    if not show_debug_grid:
        ax.grid(False)
        ax.axis('off')
        ax.set_facecolor('xkcd:black')
        fig.set_facecolor('xkcd:black')
    # make it tight
    fig.tight_layout()
    return ax, fig

# def save_image_from_grid(x_vals, y_vals, z_vals, elevation=30, xy_angle=-60, zoom=0, filename=None):
def save_image_from_grid(x_vals, y_vals, z_vals, elevation=-19, xy_angle=67, zoom=None, filename=None, show_debug_grid=False):
    ax, fig = generate_image(x_vals, y_vals, z_vals, elevation, xy_angle, zoom, show_debug_grid)
    plt.savefig(filename, edgecolor='xkcd:black', facecolor='xkcd:black')
    plt.close(fig)

def show_image_from_grid(x_vals, y_vals, z_vals, elevation=-19, xy_angle=67, zoom=None, filename=None, show_debug_grid=False):
    ax, fig = generate_image(x_vals, y_vals, z_vals, elevation, xy_angle, zoom, show_debug_grid)
    plt.show()
    plt.close(fig)

def positions_from_grid(grid):
    """
    Takes the grid and returns coordinates, starting from (0,0,0)->(dimX,dimY,dimZ)
    """
    return np.nonzero(grid)

def generate_grid(dimX, dimY, dimZ):
    return np.zeros((dimX, dimY, dimZ))

def generate_grid_with_frames(frames, dimX, dimY, dimZ):
    return np.zeros((frames, dimX, dimY, dimZ))

if __name__=='__main__':
    main()
