import curses
from typing import TYPE_CHECKING, Literal, Tuple, List
from render.utils import (
    fcode_opt as fco, blend_rgba_img_onto_rgb_img_inplace, 
    first_diff_color, last_diff_color, lesser, greater, draw_line,
    get_diff_intervals, combine_intervals, distances_to_false, get_false_chunk_sizes
)
from draw_utils import print3
from time import perf_counter
from threading import Thread
from logger import Logger
import numpy as np
from render.font import Font
from render.constants import CameraConstants
from gd_constants import GDConstants

class CameraFrame:
    """
    Wrapper over a 2D array of pixels for rendering to the screen.
    
    Images with transparency can be added to a CameraFrame, however the final compiled result that gets
    printed to the screen will assume all alpha values are 255 (opaque).
    """

    def __init__(self, size: Tuple[int | None, int | None] = (None, None), pos: Tuple[int | None, int | None] = (0, 0)) -> None:
        """ Optional params:
        - `size`: tuple (width, height) in pixels. None values will default to the terminal's width/height.
        - `pos`: tuple (x, y) in pixels, where the top left corner of the frame will be placed. Defaults to (0, 0) (top left of screen)
        
        NOTE: Height and y-position MUST both be even. Each character is 2 pixels tall, and we cant render half-characters.
        """
        
        assert size[1] is None or size[1] % 2 == 0, f"[CameraFrame/__init__]: height must be even, instead got {size[1]}"
        assert pos[1] is None or pos[1] % 2 == 0, f"[CameraFrame/__init__]: y position must be even, instead got {pos[1]}"
        
        self.width = size[0] if size[0] is not None else GDConstants.term.width
        """ Width in pixels (1px = width of 1 monospaced character) """
        self.height = size[1] if size[1] is not None else GDConstants.term.height*2
        """ Height in pixels (2px = height of 1 monospaced character) """
        
        self.pos = pos
        
        self.initialized_colors = set()
        """ Set of color pairs that have been initialized. """
        
        self.pixels: np.ndarray = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        """ 2d array of pixels. Each pixel is an rgb tuple. (0, 0) is the top left of the frame, not the top left of the screen. """

    def render_raw(self) -> None:
        """ Simply prints the frame to the screen, without the need for a previous frame. 
        Keep in mind, this is quite slow and should only be used for rendering the first frame. """
        
        # handle odd starting y. NOTE - this wont happen for now, since we are requiring even starting y and height.
        if self.pos[1] % 2 == 1:
            # first line prints bottom half char (top half will be terminal default bg)
            string1 = ""
            for j in range(self.width):
                string1 += fco(self.pixels[self.pos[1],j], None) + '▀'
            print3(GDConstants.term.move_xy(self.pos[0], self.pos[1]//2) + string1)
            
            # print middle rows
            stop_at = (self.pos[1] + self.height - (self.pos[1] + self.height) % 2) - 1
            # if height is even there will be an extra line at the end
            # if odd, then we just go until the end right here, since there is no last isolated line
            for i in range(self.pos[1]+1, stop_at):
                string = ""
                for j in range(self.width):
                    string += fco(self.pixels[i,j], self.pixels[i+1,j]) + '▀'
                print3(GDConstants.term.move_xy(self.pos[0], i//2) + string)
                
            # print last line if needed
            if self.height % 2 == 0: # since y is odd, if height is even, then we have another case of a single line
                string2 = ""
                for j in range(self.width):
                    string2 += fco(None, self.pixels[self.pos[1]+self.height-1,j]) + '▀'
                print3(GDConstants.term.move_xy(self.pos[0], (self.pos[1]+self.height)//2 + 1) + string2)
            
        else:
            
            #compiled_str = "" # try printing the whole thing at once
            
            for i in range(0, self.height, 2):
                string = ""
                for j in range(self.width):
                    string += fco(self.pixels[i,j], self.pixels[i+1,j]) + '▀' # for quick copy: ▀
                
                #compiled_str += string + "\n"
                print3(GDConstants.term.move_xy(self.pos[0], (i+self.pos[1])//2) + string)
            #print3(GDConstants.term.move_xy(self.pos[0], self.pos[1]//2) + compiled_str)

    def curses_render_raw(self) -> None:
        for top_row_index in range(0, self.height, 2):       
            screen_y = top_row_index // 2
            for j in range(len(self.pixels[top_row_index])):
                #string += fco(self.pixels[top_row_index,j], self.pixels[top_row_index+1,j]) + '▀' # pixels1 is top, so it gets fg color. pixels2 is bottom, so it gets bg color.
                # TODO - cant use color codes - need to use curses.initcolor
                # ^^ maybe make a color cache???? using rgb tuples -> curses color id
                
                # calculate key of color
                fg_grayscale_value = np.mean(self.pixels[top_row_index,j]) # 0-255
                bg_grayscale_value = np.mean(self.pixels[top_row_index+1,j]) # 0-255
                
                # scale each down to 0-15 (from 0-255)
                scaled_fg = int(fg_grayscale_value / 255 * 15)
                scaled_bg = int(bg_grayscale_value / 255 * 15)
                
                # combine into 8-bit number
                color_key = (scaled_fg << 4) + scaled_bg
                
                color_key = max(1, color_key)
                
                if color_key not in self.initialized_colors:
                    # initialize the color pair
                    fg_1000_based = int(scaled_fg / 15 * 1000)
                    bg_1000_based = int(scaled_bg / 15 * 1000)
                    #Logger.log(f"scaled fg: {scaled_fg}, scaled bg: {scaled_bg}, fg_1000_based: {fg_1000_based}, bg_1000_based: {bg_1000_based}")
                    curses.init_color(scaled_fg << 4, fg_1000_based, fg_1000_based, fg_1000_based)
                    curses.init_color(scaled_bg, bg_1000_based, bg_1000_based, bg_1000_based)
                    Logger.log(f"rend raw: color key: {color_key}, fg: {scaled_fg << 4}, bg: {scaled_bg}")
                    curses.init_pair(color_key, scaled_fg << 4, scaled_bg)
                    self.initialized_colors.add(color_key)                        
                
                #Logger.log(f"printing at yx {screen_y}, {j} with color key {color_key}")
                GDConstants.screen.addch(screen_y, j, "▀", curses.color_pair(color_key))
        
        #Logger.log(f"[CameraFrame/render]: Appending ({print_start}, {print_end}) to indices_to_print, which currently has {len(indices_to_print)} elements (b4 adding)")
        #indices_to_print.append((print_start, print_end))
        
        #Logger.log(f"(raw) refreshing curses screen")
        GDConstants.screen.refresh()

    # XXX - main render func, This can still be improved by adding a huge chunk of pixels at once
    # if there is a lot of pixels with the same color, then skipping to the next different color
    def render(self, prev_frame: "CameraFrame") -> None:
        """ Prints the frame to the screen.
        Optimized by only printing the changes from the previous frame. """
        
        final_string = ""

        i = 0
        for top_row_index in range(0, self.height, 2):       
            first_diff_row1 = first_diff_color(self.pixels[top_row_index], prev_frame.pixels[top_row_index])
            first_diff_row2 = first_diff_color(self.pixels[top_row_index+1], prev_frame.pixels[top_row_index+1])
            
            last_diff_row1 = last_diff_color(self.pixels[top_row_index], prev_frame.pixels[top_row_index])
            last_diff_row2 = last_diff_color(self.pixels[top_row_index+1], prev_frame.pixels[top_row_index+1])
            
            print_start = lesser(first_diff_row1, first_diff_row2)
            print_end = greater(last_diff_row1, last_diff_row2)
            
            start, end = print_start, print_end
            
            # if both are None, that means the rows were the exact same, so we don't need to print anything
            if start is None and end is None:
                #Logger.log(f"Skipping row {i} since it's the same as the previous row!")
                i += 1
                continue

            final_string += GDConstants.term.move_xy(int(start)+self.pos[0], i+self.pos[1]//2)
            string = ""
            # get a numpy array of which indices are repeat colors (so we can skip fcode)
            color_strip = self.pixels[i*2:i*2+2, start:end+1]
            colors_diffs = np.any(color_strip[:, 1:] != color_strip[:, :-1], axis=(0, 2))
            """ [diff(1, 0), diff(2, 1), ...]. True if different, False if same. """
            #Logger.log(f"color strip 1 first 5: {color_strip[0, :5]}")
            #Logger.log(f"color strip 2 first 5: {color_strip[1, :5]}")
            #
            #Logger.log(f"colors_diffs: {colors_diffs[:5]}")
            
            # add the first pixel
            string += fco(self.pixels[i*2,start], self.pixels[i*2+1,start]) + '▀'

            for j in range(start+1, end+1):
                # if colors_diffs is True for the current pixel, that means the colors are different from the previous pixel
                # in that case we have to re-fcode
                if colors_diffs[j-start-1]:
                    string += fco(self.pixels[i*2,j], self.pixels[i*2+1,j]) + '▀'
                else:
                    string += '▀'
            # while loop ize ^^^

            #Logger.log(f"[CameraFrame/render]: str construction: {perf_counter()-start_time_2:4f}")
            # go to coordinates in terminal, and print the string
            # terminal coordinates: start, i
            
            #Logger.log_on_screen(GDConstants.term, f"[CameraFrame/render]: printing@{int(start) + self.pos[0]}, {i + self.pos[1]//2} for len {end-start+1}")
            #Logger.log_on_screen(GDConstants.term, f"[CameraFrame/render]: printing@{int(start) + self.pos[0]},{i + self.pos[1]//2}: \x1b[0m[{string}\x1b[0m]")
            #start_time_2 = perf_counter()
           # print3(GDConstants.term.move_xy(int(start)+self.pos[0], i+self.pos[1]//2) + string)
            #print_buffer.append(((int(start)+self.pos[0], i+self.pos[1]//2), string))
            final_string += string
            i += 1
            #Logger.log(f"[CameraFrame/render]: strlen={len(string)}: {perf_counter()-start_time_2:4f}")
        
        # combine all the print calls into a single call
        #for coords, string in print_buffer:
        #    final_string += GDConstants.term.move_xy(*coords) + string
            
        print3(final_string)
        
        #Logger.log(f"[CameraFrame/render]: print to terminal: {perf_counter()-start_time:4f}")
    
    # similar to func above, but should be rendering even less (only intervals of diffs, not first change -> last change)
    # so idk why tf this one is so much slower
    def render_intervaled(self, prev_frame: "CameraFrame") -> None:
        """ Prints the frame to the screen.
        Optimized by only printing the changes from the previous frame. """
        
        final_string = ""

        i = 0
        for top_row_index in range(0, self.height, 2):       
            row1_diff_intervals = get_diff_intervals(self.pixels[top_row_index], prev_frame.pixels[top_row_index])
            row2_diff_intervals = get_diff_intervals(self.pixels[top_row_index+1], prev_frame.pixels[top_row_index+1])
            
            combined_intervals: List[Tuple[int, int]] = combine_intervals(*row1_diff_intervals, *row2_diff_intervals)
            """ List of (starts -> ends) on which this strip of pixels is different from the previous frame. 
            Only render pixels along these intervals. """
            
            if len(combined_intervals) == 0: # if there are no differences, skip this row
                i += 1
                continue
            
            color_strip = self.pixels[i*2:i*2+2,:]
            colors_diffs = np.any(color_strip[:, 1:] != color_strip[:, :-1], axis=(0, 2))
            """ [diff(1, 0), diff(2, 1), ...]. True if different, False if same. """

            for interval in combined_intervals:
                
                start, end = interval
                # end is exclusive
                
                # goto the start of the interval
                final_string += GDConstants.term.move_xy(start+self.pos[0], i+self.pos[1]//2)
                
                # add the first pixel
                string = fco(self.pixels[i*2,start], self.pixels[i*2+1,start]) + '▀'

                for j in range(start+1, end):
                    # if colors_diffs is True for the current pixel, that means the colors are different from the previous pixel
                    # in that case we have to re-fcode
                    if colors_diffs[j-1]:
                        string += fco(self.pixels[i*2,j], self.pixels[i*2+1,j]) + '▀'
                    else:
                        string += '▀'
               
                final_string += string
                
            i += 1
            #Logger.log(f"[CameraFrame/render]: strlen={len(string)}: {perf_counter()-start_time_2:4f}")
        
        # combine all the print calls into a single call
        #for coords, string in print_buffer:
        #    final_string += GDConstants.term.move_xy(*coords) + string
            
        print3(final_string)
        
        #Logger.log(f"[CameraFrame/render]: print to terminal: {perf_counter()-start_time:4f}")
    
    def render_bufferlist(self, prev_frame: "CameraFrame") -> None:
        """ Prints the frame to the screen.
        Optimized by only printing the changes from the previous frame. """
        
        indices_to_print = []
        """ Should end up being a list of tuples (start, end) 
        where start and end are the first and last changed "pixels columns" (characters) in a row. """

        for top_row_index in range(0, self.height, 2):       
            first_diff_row1 = first_diff_color(self.pixels[top_row_index], prev_frame.pixels[top_row_index])
            first_diff_row2 = first_diff_color(self.pixels[top_row_index+1], prev_frame.pixels[top_row_index+1])
            
            last_diff_row1 = last_diff_color(self.pixels[top_row_index], prev_frame.pixels[top_row_index])
            last_diff_row2 = last_diff_color(self.pixels[top_row_index+1], prev_frame.pixels[top_row_index+1])
            
            print_start = lesser(first_diff_row1, first_diff_row2)
            print_end = greater(last_diff_row1, last_diff_row2)
            
            #Logger.log(f"[CameraFrame/render]: Appending ({print_start}, {print_end}) to indices_to_print, which currently has {len(indices_to_print)} elements (b4 adding)")
            indices_to_print.append((print_start, print_end))
        
        #Logger.log(f"[CameraFrame/render]: get indices to print: {1000*(perf_counter()-start_time):4f}ms")
        # printing the frame
        # for each pair of rows, convert the pixels from start to end into colored characters, then print.
        
        print_buffer: List[Tuple[Tuple[int, int], str]] = []
        """
        Buffer that stores locations as 2-tuples (representing where to term.goto) and the string to print there.
        
        This allows us to only use the print function a single time, which is much faster than calling it for each pixel.
        """
        
        for i in range(len(indices_to_print)):
            #Logger.log(f"[CameraFrame/render]: row {i} indices to print: {indices_to_print[i]}")
            start, end = indices_to_print[i]
            
            # if both are None, that means the rows were the exact same, so we don't need to print anything
            if start is None and end is None:
                #Logger.log(f"Skipping row {i} since it's the same as the previous row!")
                continue
            
            # converting the two pixel rows into a string
            string = ""
            
            # get a numpy array of which indices are repeat colors (so we can skip fcode)
            color_strip = self.pixels[i*2:i*2+2, start:end+1]
            colors_diffs = np.any(color_strip[:, 1:] != color_strip[:, :-1], axis=(0, 2))
            
            # add the first pixel
            string += fco(self.pixels[i*2,start], self.pixels[i*2+1,start]) + '▀'

            for j in range(start+1, end+1):
                # if colors_diffs is True for the current pixel, that means the colors are different from the previous pixel
                # in that case we have to re-fcode
                if colors_diffs[j-start-1]:
                    string += fco(self.pixels[i*2,j], self.pixels[i*2+1,j]) + '▀'
                else:
                    string += '▀'
                
            # add the last few pixels if needed, but theyre all the same
            #if pixel_idx < end-start+1:
            #    string += '▀' * (end-start+1 - pixel_idx)
            #for j in range(start+1, end+1):
                # if colors are the same as previous pixel, only add the pixel
                #if colors_diffs[j-start-1]:
                #    string += fco(self.pixels[i*2,j], self.pixels[i*2+1,j]) + '▀' # pixels1 is top, so it gets fg color. pixels2 is bottom, so it gets bg color.
                #else:
                #    string += '▀'
                    
            #Logger.log(f"[CameraFrame/render]: str construction: {perf_counter()-start_time_2:4f}")
            # go to coordinates in terminal, and print the string
            # terminal coordinates: start, i
            
            #Logger.log_on_screen(GDConstants.term, f"[CameraFrame/render]: printing@{int(start) + self.pos[0]}, {i + self.pos[1]//2} for len {end-start+1}")
            #Logger.log_on_screen(GDConstants.term, f"[CameraFrame/render]: printing@{int(start) + self.pos[0]},{i + self.pos[1]//2}: \x1b[0m[{string}\x1b[0m]")
            #start_time_2 = perf_counter()
           # print3(GDConstants.term.move_xy(int(start)+self.pos[0], i+self.pos[1]//2) + string)
            print_buffer.append(((int(start)+self.pos[0], i+self.pos[1]//2), string))
            #Logger.log(f"[CameraFrame/render]: strlen={len(string)}: {perf_counter()-start_time_2:4f}")
        
        # combine all the print calls into a single call
        final_string = ""
        for coords, string in print_buffer:
            final_string += GDConstants.term.move_xy(*coords) + string
            
        print3(final_string)
        
        #Logger.log(f"[CameraFrame/render]: print to terminal: {perf_counter()-start_time:4f}")
    
    def render_usingwhile(self, prev_frame: "CameraFrame") -> None:
        """ Prints the frame to the screen.
        Optimized by only printing the changes from the previous frame. """
        
        final_string = ""

        i = 0
        for top_row_index in range(0, self.height, 2):       
            first_diff_row1 = first_diff_color(self.pixels[top_row_index], prev_frame.pixels[top_row_index])
            first_diff_row2 = first_diff_color(self.pixels[top_row_index+1], prev_frame.pixels[top_row_index+1])
            
            last_diff_row1 = last_diff_color(self.pixels[top_row_index], prev_frame.pixels[top_row_index])
            last_diff_row2 = last_diff_color(self.pixels[top_row_index+1], prev_frame.pixels[top_row_index+1])
            
            print_start = lesser(first_diff_row1, first_diff_row2)
            print_end = greater(last_diff_row1, last_diff_row2)
            
            start, end = print_start, print_end
            
            # if both are None, that means the rows were the exact same, so we don't need to print anything
            if start is None and end is None:
                #Logger.log(f"Skipping row {i} since it's the same as the previous row!")
                i += 1
                continue

            final_string += GDConstants.term.move_xy(int(start)+self.pos[0], i+self.pos[1]//2)
            string = ""
            # get a numpy array of which indices are repeat colors (so we can skip fcode)
            color_strip = self.pixels[i*2:i*2+2, start:end+1]
            colors_diffs = np.any(color_strip[:, 1:] != color_strip[:, :-1], axis=(0, 2))
            """ [diff(1, 0), diff(2, 1), ...]. True if different, False if same. """
            
            chunks_of_repeated_colors = get_false_chunk_sizes(colors_diffs)
            
            #Logger.log(f"color strip 1 first 5: {color_strip[0, :5]}")
            #Logger.log(f"color strip 2 first 5: {color_strip[1, :5]}")
            #
            #Logger.log(f"colors_diffs: {colors_diffs[:5]}")
            
            # add the first pixel
            string += fco(self.pixels[i*2,start], self.pixels[i*2+1,start]) + '▀'

            #for j in range(start+1, end+1):
            #    # if colors_diffs is True for the current pixel, that means the colors are different from the previous pixel
            #    # in that case we have to re-fcode
            #    if colors_diffs[j-start-1]:
            #        string += fco(self.pixels[i*2,j], self.pixels[i*2+1,j]) + '▀'
            #    else:
            #        string += '▀'
            # while loop ize ^^^
            j = start + 1
            num_chunks_covered = 0
            while j <= end:
                # if pixel@j diff from previous, calculate fcode
                if colors_diffs[j-start-1]:
                    string += fco(self.pixels[i*2,j], self.pixels[i*2+1,j]) + '▀'
                    j += 1
                else: # take the next chunk of Falses (same colors), add that number of pixels, and skip to the next True
                    string += '▀' * chunks_of_repeated_colors[num_chunks_covered]
                    j += chunks_of_repeated_colors[num_chunks_covered] + 1
                    num_chunks_covered += 1
                    
            #Logger.log(f"[CameraFrame/render]: str construction: {perf_counter()-start_time_2:4f}")
            # go to coordinates in terminal, and print the string
            # terminal coordinates: start, i
            
            #Logger.log_on_screen(GDConstants.term, f"[CameraFrame/render]: printing@{int(start) + self.pos[0]}, {i + self.pos[1]//2} for len {end-start+1}")
            #Logger.log_on_screen(GDConstants.term, f"[CameraFrame/render]: printing@{int(start) + self.pos[0]},{i + self.pos[1]//2}: \x1b[0m[{string}\x1b[0m]")
            #start_time_2 = perf_counter()
           # print3(GDConstants.term.move_xy(int(start)+self.pos[0], i+self.pos[1]//2) + string)
            #print_buffer.append(((int(start)+self.pos[0], i+self.pos[1]//2), string))
            final_string += string
            i += 1
            #Logger.log(f"[CameraFrame/render]: strlen={len(string)}: {perf_counter()-start_time_2:4f}")
        
        # combine all the print calls into a single call
        #for coords, string in print_buffer:
        #    final_string += GDConstants.term.move_xy(*coords) + string
            
        print3(final_string)
    
    # experimental, isnt working (but kinda close to, but i have no time to fix)
    def render2_usingdists(self, prev_frame: "CameraFrame") -> None:
        """ Prints the frame to the screen.
        Optimized by only printing the changes from the previous frame. """
        
        indices_to_print = []
        """ Should end up being a list of tuples (start, end) 
        where start and end are the first and last changed "pixels columns" (characters) in a row. """
        
        # compare the curr frame with the previous frame
        # for each pair of rows, find the first and last changed column
        # multiply term height by 2 since chars are 2 pixels tall
        start_time = perf_counter()
        times = {}
        
        #Logger.log(f"CF render begin -------------------------------")
        
        for top_row_index in range(0, self.height, 2):       
            first_diff_row1 = first_diff_color(self.pixels[top_row_index], prev_frame.pixels[top_row_index])
            first_diff_row2 = first_diff_color(self.pixels[top_row_index+1], prev_frame.pixels[top_row_index+1])
            
            last_diff_row1 = last_diff_color(self.pixels[top_row_index], prev_frame.pixels[top_row_index])
            last_diff_row2 = last_diff_color(self.pixels[top_row_index+1], prev_frame.pixels[top_row_index+1])
            
            print_start = lesser(first_diff_row1, first_diff_row2)
            print_end = greater(last_diff_row1, last_diff_row2)
            
            #Logger.log(f"[CameraFrame/render]: Appending ({print_start}, {print_end}) to indices_to_print, which currently has {len(indices_to_print)} elements (b4 adding)")
            indices_to_print.append((print_start, print_end))
        
        #Logger.log(f"[CameraFrame/render]: get indices to print: {1000*(perf_counter()-start_time):4f}ms")
        # printing the frame
        # for each pair of rows, convert the pixels from start to end into colored characters, then print.
        
        print_buffer: List[Tuple[Tuple[int, int], str]] = []
        """
        Buffer that stores locations as 2-tuples (representing where to term.goto) and the string to print there.
        
        This allows us to only use the print function a single time, which is much faster than calling it for each pixel.
        """
        
        for i in range(len(indices_to_print)):
            #Logger.log(f"[CameraFrame/render]: row {i} indices to print: {indices_to_print[i]}")
            start, end = indices_to_print[i]
            
            # if both are None, that means the rows were the exact same, so we don't need to print anything
            if start is None and end is None:
                #Logger.log(f"Skipping row {i} since it's the same as the previous row!")
                continue
            
            # converting the two pixel rows into a string
            string = ""
            
            # get a numpy array of which indices are repeat colors (so we can skip fcode)
            color_strip = self.pixels[i*2:i*2+2, start:end+1]
            colors_diffs = np.any(color_strip[:, 1:] != color_strip[:, :-1], axis=(0, 2))
            
            distances_to_next_diff = distances_to_false(colors_diffs)
            
            # add the first pixel
            string += fco(self.pixels[i*2,start], self.pixels[i*2+1,start]) + '▀'

            num_diffs_passed = 0
            
            for j in range(start+1, end+1):
                # if colors_diffs is True for the current pixel, that means the colors are different from the previous pixel
                # in that case we have to re-fcode
                if colors_diffs[j-start-1]:
                    string += fco(self.pixels[i*2,j], self.pixels[i*2+1,j]) + '▀'
                    num_diffs_passed += 1
                else: # add a ton of pixels at once, then increment j
                    string += '▀' * distances_to_next_diff[num_diffs_passed]
                    j += distances_to_next_diff[num_diffs_passed] + 1
            
            #j = start + 1
            #while j < end+1:
            #    # if colors_diffs is True for the current pixel, that means the colors are different from the previous pixel
            #    # in that case we have to re-fcode
            #    if colors_diffs[j-start-1]:
            #        string += fco(self.pixels[i*2,j], self.pixels[i*2+1,j]) + '▀'
            #        num_diffs_passed += 1
            #        j += 1
            #    else: # add a ton of pixels at once, then increment j
            #        string += '▀' * distances_to_next_diff[num_diffs_passed]
            #        j += distances_to_next_diff[num_diffs_passed] + 1


            print_buffer.append(((int(start)+self.pos[0], i+self.pos[1]//2), string))

        # combine all the print calls into a single call
        final_string = ""
        for coords, string in print_buffer:
            final_string += GDConstants.term.move_xy(*coords) + string
            
        print3(final_string)
        
        #Logger.log(f"[CameraFrame/render]: print to terminal: {perf_counter()-start_time:4f}")
           
    # experimental, isnt working yet
    def render3_iterpixelidxs(self, prev_frame: "CameraFrame") -> None:
        """ Prints the frame to the screen.
        Optimized by only printing the changes from the previous frame. """
        
        indices_to_print = []
        """ Should end up being a list of tuples (start, end) 
        where start and end are the first and last changed "pixels columns" (characters) in a row. """
        
        # compare the curr frame with the previous frame
        # for each pair of rows, find the first and last changed column
        # multiply term height by 2 since chars are 2 pixels tall
        start_time = perf_counter()
        times = {}
        
        #Logger.log(f"CF render begin -------------------------------")
        
        for top_row_index in range(0, self.height, 2):       
            first_diff_row1 = first_diff_color(self.pixels[top_row_index], prev_frame.pixels[top_row_index])
            first_diff_row2 = first_diff_color(self.pixels[top_row_index+1], prev_frame.pixels[top_row_index+1])
            
            last_diff_row1 = last_diff_color(self.pixels[top_row_index], prev_frame.pixels[top_row_index])
            last_diff_row2 = last_diff_color(self.pixels[top_row_index+1], prev_frame.pixels[top_row_index+1])
            
            print_start = lesser(first_diff_row1, first_diff_row2)
            print_end = greater(last_diff_row1, last_diff_row2)
            
            #Logger.log(f"[CameraFrame/render]: Appending ({print_start}, {print_end}) to indices_to_print, which currently has {len(indices_to_print)} elements (b4 adding)")
            indices_to_print.append((print_start, print_end))
        
        #Logger.log(f"[CameraFrame/render]: get indices to print: {1000*(perf_counter()-start_time):4f}ms")
        # printing the frame
        # for each pair of rows, convert the pixels from start to end into colored characters, then print.
        
        print_buffer: List[Tuple[Tuple[int, int], str]] = []
        """
        Buffer that stores locations as 2-tuples (representing where to term.goto) and the string to print there.
        
        This allows us to only use the print function a single time, which is much faster than calling it for each pixel.
        """
        
        for i in range(len(indices_to_print)):
            #Logger.log(f"[CameraFrame/render]: row {i} indices to print: {indices_to_print[i]}")
            start, end = indices_to_print[i]
            
            # if both are None, that means the rows were the exact same, so we don't need to print anything
            if start is None and end is None:
                #Logger.log(f"Skipping row {i} since it's the same as the previous row!")
                continue
            
            # converting the two pixel rows into a string
            string = ""
            start_time_2 = perf_counter()
            
            # get a numpy array of which indices are repeat colors (so we can skip fcode)
            color_strip = self.pixels[i*2:i*2+2, start:end+1]
            colors_diffs = np.any(color_strip[:, 1:] != color_strip[:, :-1], axis=(0, 2))
            # [diff(0, 1), diff(1, 2), ... diff(n-1, n)]
            
            dists_to_diffs = distances_to_false(colors_diffs)
            
            # add the first pixel
            string += fco(self.pixels[i*2,start], self.pixels[i*2+1,start]) + '▀'
            
            pixel_idx = 1 # index of the pixel we are currently at
            for dist in dists_to_diffs:
                # add dist * pixels, since they are all the same (so we dont need to fcode again)
                # after that, add the next pixel; it has a different color
                string += '▀' * dist
                string += fco(self.pixels[i*2,start+pixel_idx], self.pixels[i*2+1,start+pixel_idx]) + '▀'
                pixel_idx += dist + 1
                
            # add the last few pixels if needed, but theyre all the same
            #if pixel_idx < end-start+1:
            #    string += '▀' * (end-start+1 - pixel_idx)
            #for j in range(start+1, end+1):
                # if colors are the same as previous pixel, only add the pixel
                #if colors_diffs[j-start-1]:
                #    string += fco(self.pixels[i*2,j], self.pixels[i*2+1,j]) + '▀' # pixels1 is top, so it gets fg color. pixels2 is bottom, so it gets bg color.
                #else:
                #    string += '▀'
                    
            #Logger.log(f"[CameraFrame/render]: str construction: {perf_counter()-start_time_2:4f}")
            # go to coordinates in terminal, and print the string
            # terminal coordinates: start, i
            
            #Logger.log_on_screen(GDConstants.term, f"[CameraFrame/render]: printing@{int(start) + self.pos[0]}, {i + self.pos[1]//2} for len {end-start+1}")
            #Logger.log_on_screen(GDConstants.term, f"[CameraFrame/render]: printing@{int(start) + self.pos[0]},{i + self.pos[1]//2}: \x1b[0m[{string}\x1b[0m]")
            #start_time_2 = perf_counter()
           # print3(GDConstants.term.move_xy(int(start)+self.pos[0], i+self.pos[1]//2) + string)
            print_buffer.append(((int(start)+self.pos[0], i+self.pos[1]//2), string))
            #Logger.log(f"[CameraFrame/render]: strlen={len(string)}: {perf_counter()-start_time_2:4f}")
        
        # combine all the print calls into a single call
        final_string = ""
        for coords, string in print_buffer:
            final_string += GDConstants.term.move_xy(*coords) + string
            
        print3(final_string)
        
        #Logger.log(f"[CameraFrame/render]: print to terminal: {perf_counter()-start_time:4f}")
    
    # VERY SLOW AND BROKEN (sad)
    def curses_render(self, prev_frame: "CameraFrame") -> None:
        """ new curses-based renderer test """
        
        self.initialized_colors = set()
        
        #indices_to_print = []
        #""" Should end up being a list of tuples (start, end) 
        #where start and end are the first and last changed "pixels columns" (characters) in a row. """
        
        # compare the curr frame with the previous frame
        # for each pair of rows, find the first and last changed column
        # multiply term height by 2 since chars are 2 pixels tall
        for top_row_index in range(0, self.height, 2):       
            #first_diff_row1 = first_diff_color(self.pixels[top_row_index], prev_frame.pixels[top_row_index])
            #first_diff_row2 = first_diff_color(self.pixels[top_row_index+1], prev_frame.pixels[top_row_index+1])
            
            #last_diff_row1 = last_diff_color(self.pixels[top_row_index], prev_frame.pixels[top_row_index])
            #last_diff_row2 = last_diff_color(self.pixels[top_row_index+1], prev_frame.pixels[top_row_index+1])
            
            row1_diff_intervals = get_diff_intervals(self.pixels[top_row_index], prev_frame.pixels[top_row_index])
            row2_diff_intervals = get_diff_intervals(self.pixels[top_row_index+1], prev_frame.pixels[top_row_index+1])
            
            combined_intervals: List[Tuple[int, int]] = combine_intervals(*row1_diff_intervals, *row2_diff_intervals)
            
            #Logger.log(f"combined intervals: {combined_intervals}")
            
            # render
            screen_y = top_row_index // 2
            for interval in combined_intervals:
                # example interval: (17, 29)
                
                for j in range(interval[0], interval[1]-1):
                    # calculate key of color
                    fg_grayscale_value = np.mean(self.pixels[top_row_index,j]) # 0-255
                    bg_grayscale_value = np.mean(self.pixels[top_row_index+1,j]) # 0-255
                    
                    # scale each down to 0-15 (from 0-255)
                    scaled_fg = int(fg_grayscale_value / 255 * 15)
                    scaled_bg = int(bg_grayscale_value / 255 * 15)
                    
                    # combine into 8-bit number
                    color_key = (scaled_fg << 4) + scaled_bg
                    
                    color_key = max(1, color_key) # cant use 0 lol
                    
                    if color_key not in self.initialized_colors:
                        # initialize the color pair
                        fg_1000_based = int(scaled_fg / 15 * 1000)
                        bg_1000_based = int(scaled_bg / 15 * 1000)
                        curses.init_color(scaled_fg << 4, fg_1000_based, fg_1000_based, fg_1000_based)
                        curses.init_color(scaled_bg, bg_1000_based, bg_1000_based, bg_1000_based)
                        Logger.log(f"attempting to init color pair {color_key} with fg {scaled_fg << 4} and bg {scaled_bg}")
                        curses.init_pair(color_key, scaled_fg << 4, scaled_bg)
                        self.initialized_colors.add(color_key)   
                    #string = "▀"                 
                    
                    #Logger.log(f"(render) at yx {screen_y}, {j} string of len 1")
                    GDConstants.screen.addch(screen_y, j, "▀", curses.color_pair(color_key))
            
            #Logger.log(f"[CameraFrame/render]: Appending ({print_start}, {print_end}) to indices_to_print, which currently has {len(indices_to_print)} elements (b4 adding)")
            #indices_to_print.append((print_start, print_end))
        
        Logger.log(f"(render) refreshing curses screen")
        GDConstants.screen.refresh()
    
    def fill(self, color: CameraConstants.RGBTuple) -> None:
        """ Fills the entire canvas with the given color. RGB (3-tuple) required. Should be pretty efficient because of numpy. """
        assert len(color) == 3, f"[FrameLayer/fill]: color must be an rgb (3 ints) tuple, instead got {color}"
        self.pixels[:,:] = color
        
    def fill_with_gradient(
        self, 
        color1: CameraConstants.RGBTuple, 
        color2: CameraConstants.RGBTuple, 
        direction: Literal["horizontal", "vertical"] = "horizontal"
        ) -> None:
        """ Fills the entire canvas with a gradient from color1 to color2.
        The gradient can be either horizontal or vertical. """
        
        # create a gradient
        if direction == "horizontal":
            gradient = np.linspace(color1, color2, self.width)
            
            # fill each row with the gradient
            for i in range(self.height):
                self.pixels[i] = gradient
            
        elif direction == "vertical":
            gradient = np.linspace(color1, color2, self.height)
            
            for i in range(self.width):
                self.pixels[:,i] = gradient

    Anchor = Literal[
        "top-left", 
        "top-right", 
        "bottom-left", 
        "bottom-right", 
        "center",
        "top",
        "bottom",
        "left",
        "right"
    ]
    def add_rect(
        self, 
        color: CameraConstants.RGBTuple | CameraConstants.RGBATuple, 
        x: int, y: int, 
        width: int, height: int,
        outline_width: int = 0,
        outline_color: CameraConstants.RGBTuple | CameraConstants.RGBATuple = (0,0,0,0),
        anchor: Anchor = "top-left",
        ) -> None:
        """ Places a rectangle on the frame with the given RGBA color and position.
        Optionally, can add an outline to the rectangle with the given width and color. 
        Can also specify what part of the rectangle x and y refer to. (default is top left)"""

        # add alpha to color/outline if it's an rgb tuple
        
        if color is None:
            return
        
        if len(color) == 3:
            color = (*color, 255)
        if len(outline_color) == 3:
            outline_color = (*outline_color, 255)
            
        x = round(x)
        y = round(y)
        width = round(width)
        height = round(height)
            
        rect_as_pixels = np.full((height+outline_width*2, width+outline_width*2, 4), outline_color, dtype=np.uint8)
        
        # set the middle of rect_as_pixels to the color
        rect_as_pixels[outline_width:outline_width+height, outline_width:outline_width+width] = color
        
        y1 = y - outline_width
        y2 = y + height + outline_width
        x1 = x - outline_width
        x2 = x + width + outline_width
        
        match(anchor):
            case "top-right":
                x1 -= width
                x2 -= width
            case "bottom-left":
                y1 -= height
                y2 -= height
            case "bottom-right":
                x1 -= width
                x2 -= width
                y1 -= height
                y2 -= height
            case "center":
                x1 -= width // 2
                x2 -= width // 2
                y1 -= height // 2
                y2 -= height // 2
            case "top":
                x1 -= width // 2
                x2 -= width // 2
            case "bottom":
                x1 -= width // 2
                x2 -= width // 2
                y1 -= height
                y2 -= height
            case "left":
                y1 -= height // 2
                y2 -= height // 2
            case "right":
                y1 -= height // 2
                y2 -= height // 2
                x1 -= width
                x2 -= width
        
        # if any coords go out of bounds, set it to the edge of the frame and clip the rect_as_pixels
        clipped_y1 = max(0, y1)
        clipped_y2 = min(self.height, y2)
        clipped_x1 = max(0, x1)
        clipped_x2 = min(self.width, x2)
        
        offset_y1 = clipped_y1 - y1
        offset_y2 = clipped_y2 - y2
        offset_x1 = clipped_x1 - x1
        offset_x2 = clipped_x2 - x2
        
        # clip the rect_as_pixels
        clipped_rect_as_pixels = rect_as_pixels[
            int(offset_y1):int(rect_as_pixels.shape[0]-offset_y2), 
            int(offset_x1):int(rect_as_pixels.shape[1]-offset_x2)
        ]
        
        blend_rgba_img_onto_rgb_img_inplace(
            self.pixels[
                clipped_y1:clipped_y2,
                clipped_x1:clipped_x2
            ], clipped_rect_as_pixels
        )
        
    def add_text(
        self, 
        x: int, y: int, 
        font: Font, 
        text: str, 
        anchor: Literal["left", "right", "center"] = "center",
        color: CameraConstants.RGBTuple | CameraConstants.RGBATuple = (255,255,255)) -> None:
        """       
        Draws a font to the pixel array at the specified x and y values, where y is the vertical center of the text,
        and x can be specified to correspond to either the left, center, or right edges of the text.
        
        x and y should be relative to the top left corner of the frame.
        
        Note: Fonts SHOULD be monospaced.
        """
        
        pixels = font.assemble(text, color)
            
        # find the top left corner where the text should be placed
        left = ...
        top = y - pixels.shape[0] // 2
        
        # match to anchor
        match(anchor):
            case "right":
                left = x - pixels.shape[1]
            case "center":
                left = x - pixels.shape[1] // 2
            case "left":
                left = x
        
        # clip to 0, 0
        clipped_left = max(0, left)
        clipped_top = max(0, top)
        
        # these should always be nonnegative
        offset_top = clipped_top - top
        offset_left = clipped_left - left
        
        # if completely offscreen, return
        #if offset_top >= pixels.shape[0] or offset_left >= pixels.shape[1]:
        #    return

        blend_rgba_img_onto_rgb_img_inplace(
            self.pixels[clipped_top:clipped_top+pixels.shape[0]-offset_top, clipped_left:clipped_left+pixels.shape[1]-offset_left],
            pixels[offset_top:, offset_left:]
        )

    def add_pixels_topleft(self, x: int, y: int, pixels: np.ndarray) -> None:
        """ Same as add_pixels, but with the anchor set to top-left. mainly for optimization. """
        #Logger.log(f"[FrameLayer/add_pixels_topleft]: adding pixels at {x}, {y}, size {pixels.shape}")

        # if x or y are negative, clip them
        clipped_y1 = max(0, y)
        #clipped_y2 = min(self.height, y+pixels.shape[0])
        clipped_x1 = max(0, x)
        #clipped_x2 = min(self.width, x+pixels.shape[1])
        
        # these should always be nonnegative
        offset_x1 = clipped_x1 - x
        #offset_x2 = clipped_x2 - x
        offset_y1 = clipped_y1 - y
        #offset_y2 = clipped_y2 - y
        
        # TODO - this shouldnt happen, but we catch just in case
        if offset_x1 >= pixels.shape[1] or offset_y1 >= pixels.shape[0]:
            #Logger.log(f"[FrameLayer/add_pixels_topleft]: clipped off all pixels, returning")
            return

        blend_rgba_img_onto_rgb_img_inplace(
            self.pixels[int(clipped_y1):int(clipped_y1+pixels.shape[0]-offset_y1), int(clipped_x1):int(clipped_x1+pixels.shape[1]-offset_x1)],
            pixels[int(offset_y1):self.height, int(offset_x1):self.width]
        )
    
    def add_pixels_centered_at(self, x: int, y: int, pixels: np.ndarray) -> None:
        """ Adds a set of pixels to the frame, with the center at the given position. """
        # find the range that would actually be visible
        # find true topleft
        
        pixels_height_1 = pixels.shape[0] // 2
        pixels_height_2 = pixels.shape[0] - pixels_height_1
        pixels_width_1 = pixels.shape[1] // 2
        pixels_width_2 = pixels.shape[1] - pixels_width_1
        
        left = x - pixels_width_1
        top = y - pixels_height_1
        
        clipped_left = int(max(0, left))
        clipped_top = int(max(0, top))
        
        offset_left = int(clipped_left - left)
        offset_top = int(clipped_top - top)
        
        # ignore if fully offscreen
        #if offset_left >= pixels_width_2 or offset_top >= pixels_height_2:
        #    return
        
        #Logger.log(f"[CameraFrame/add_pixels_centered_at]: adding pixels at {x}, {y}, size {pixels.shape}, left={left}, top={top}, clipped_left={clipped_left}, clipped_top={clipped_top}, offset_left={offset_left}, offset_top={offset_top}")
        #Logger.log(f"^^^ Final indices to use: self.pixels[{clipped_top}:{clipped_top+pixels.shape[0]-offset_top}, {clipped_left}:{clipped_left+pixels.shape[1]-offset_left}]")
        #Logger.log(f"^^^ Indices for pixels: pixels[{offset_top}:{pixels.shape[0]}, {offset_left}:{pixels.shape[1]}]")
        
        if clipped_top+pixels.shape[0]-offset_top <= 0: # if the top is offscreen
            return
        
        if clipped_left+pixels.shape[1]-offset_left <= 0: # if the left is offscreen
            return
        
        #Logger.log(f"indices for self.pixels: self.pixels[{clipped_top}:{clipped_top+pixels.shape[0]-offset_top}, {clipped_left}:{clipped_left+pixels.shape[1]-offset_left}]")
        
        blend_rgba_img_onto_rgb_img_inplace(
            self.pixels[clipped_top:int(clipped_top+pixels.shape[0]-offset_top), clipped_left:int(clipped_left+pixels.shape[1]-offset_left)],
            pixels[offset_top:, offset_left:]
        )
    
    def add_line(self, pos1: Tuple[int, int], pos2: Tuple[int, int], color: CameraConstants.RGBTuple) -> None:
        """ Draws a non-antialiased, 1-wide line between two points on the frame. """
        draw_line(self.pixels, pos1, pos2, color)
    
    def copy(self) -> "CameraFrame":
        """ Returns a deep copy of this CameraFrame. (except for the terminal reference) """
        new_frame = CameraFrame((self.width, self.height), self.pos)
        new_frame.pixels = np.copy(self.pixels)
        return new_frame