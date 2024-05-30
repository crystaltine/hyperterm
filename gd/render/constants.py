import blessed
from render.utils import nearest_quarter

class CameraUtils:
    BLOCK_WIDTH = 6 
    """ How wide a block is in pixels (half of a character: ▀) """
    BLOCK_HEIGHT = 6 
    """ How tall a block is in pixels (half of a character: ▀) """

    CAMERA_LEFT_OFFSET = 10
    """ Amount of BLOCKS the camera_left is behind the player x position """

    MIN_PLAYER_SCREEN_OFFSET = 0.25
    """ The minimum proportion of the screen height the player should be from the top of the screen, at all times.
    For example, if =0.25, then the player should never be rendered in the top 25% of the screen - the camera would move up instead. """

    MAX_PLAYER_SCREEN_OFFSET = 0.75
    """ The maximum proportion of the screen height the player should be from the top of the screen, at all times.
    For example, if =0.75, then the player should never be rendered in the bottom 25% of the screen - the camera would move down instead. """

    GROUND_HEIGHT = 4
    """ Max height of the ground in BLOCKS. This determines how much the rest of the level is "pushed up" """
    
    # for renderer only - physics runs at ~240
    # also, this is a target rate only.
    # I've tested, it still runs at ~30fps.
    RENDER_FRAMERATE = 90 
    """ Framerate of the renderer. In practice, works a bit wonky, =60 brings 1000FPS down to ~40 ish, probably because windows clock isnt super accurate. """

    def screen_width_blocks(term: blessed.Terminal) -> float:
        """
        Returns the width of the screen in BLOCKS. does NOT round.
        See `CameraUtils.BLOCK_WIDTH` for pixel width of each block.
        """

        return term.width / CameraUtils.BLOCK_WIDTH

    def screen_height_blocks(term: blessed.Terminal) -> float:
        """
        Returns the height of the screen in BLOCKS. Does NOT round.
        See `CameraUtils.BLOCK_HEIGHT` for character width of each block.
        """

        return term.height*2 / CameraUtils.BLOCK_HEIGHT
    
    def center_screen_coordinates(term: blessed.Terminal) -> list:
        """
        Returns the coordinates of the center of the screen in BLOCKS.
        """

        return [term.width//(CameraUtils.BLOCK_WIDTH*2), term.height//(CameraUtils.BLOCK_HEIGHT*2)]
    
    def grid_to_terminal_pos(gridx: float, gridy: float) -> tuple:
        """
        Converts a camera grid position (block) to the TOP LEFT CORNER of
        its equivalent pixel position. (0, 0) -> (0, 0) (top left corner of screen)
        
        For example, (0, 0) should go to (0, 0)

        Assuming one block is 4 chars wide by 4 chars tall, 
        (1, 1) would map to (4, 4).
        
        This also supports decimals.
        For example:
        - (0.1, 0.45) -> (0, 2)

        The output of this function is determined by
        `CameraUtils.BLOCK_WIDTH` and `CameraUtils.BLOCK_HEIGHT`.

        Returns tuple (x, y) of ints.
        """

        return (
            round(nearest_quarter(gridx) * CameraUtils.BLOCK_WIDTH),
            round(nearest_quarter(gridy) * CameraUtils.BLOCK_HEIGHT)
        )
        