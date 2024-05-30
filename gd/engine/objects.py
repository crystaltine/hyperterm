from copy import deepcopy

class OBJECTS:
    block0_0 = {
        "name": "block0_0",
        "hitbox_xrange": [0, 1],
        "hitbox_yrange": [0, 1],
        "hitbox_type": "solid", # die when crash into side or bottom,
        "collide_effect": "crash-block",
        "requires_click": False, # if player needs to click to activate
        "multi_activate": False,
    }
    block0_1 = {
        "name": "block0_1",
        "hitbox_xrange": [0, 1],
        "hitbox_yrange": [0, 1],
        "hitbox_type": "solid", # die when crash into side or bottom,
        "collide_effect": "crash-block",
        "requires_click": False, # if player needs to click to activate
        "multi_activate": False,
    }
    block0_2 = {
        "name": "block0_2",
        "hitbox_xrange": [0, 1],
        "hitbox_yrange": [0, 1],
        "hitbox_type": "solid", # die when crash into side or bottom,
        "collide_effect": "crash-block",
        "requires_click": False, # if player needs to click to activate
        "multi_activate": False,
    }
    block0_3 = {
        "name": "block0_3",
        "hitbox_xrange": [0, 1],
        "hitbox_yrange": [0, 1],
        "hitbox_type": "solid", # die when crash into side or bottom,
        "collide_effect": "crash-block",
        "requires_click": False, # if player needs to click to activate
        "multi_activate": False,
    }
    spike = {
        "name": "spike",
        "hitbox_xrange": [0.3, 0.7],
        "hitbox_yrange": [0.2, 0.7],
        "hitbox_type": "any-touch", # die on any hitbox touch.
        "collide_effect": "crash-spike",
        "requires_click": False, # if player needs to click to activate
        "multi_activate": False,
    }
    yellow_orb = {
        "name": "yellow_orb",
        "hitbox_xrange": [-0.2, 1.2],
        "hitbox_yrange": [0.2, 1.2],
        "hitbox_type": "any-touch", # die on any hitbox touch.
        "collide_effect": "yellow-orb",
        "requires_click": True, # if player needs to click to activate
        "multi_activate": False,
        "temp_symbol": 'y'
    }
    blue_orb = {
        "name": "blue_orb",
        "hitbox_xrange": [-0.2, 1.2],
        "hitbox_yrange": [0.2, 1.2],
        "hitbox_type": "any-touch", # die on any hitbox touch.
        "collide_effect": "blue-orb",
        "requires_click": True, # if player needs to click to activate
        "multi_activate": False,
        "temp_symbol": 'bl'
    }
    purple_orb = {
        "name": "purple_orb",
        "hitbox_xrange": [-0.2, 1.2],
        "hitbox_yrange": [0.2, 1.2],
        "hitbox_type": "any-touch", # die on any hitbox touch.
        "collide_effect": "purple-orb",
        "requires_click": True, # if player needs to click to activate
        "multi_activate": False,
        "temp_symbol": 'p'
    }
    yellow_grav_portal = {
        "name": "normal_grav_portal",
        "hitbox_xrange": [0.1, 0.9],
        "hitbox_yrange": [-1.4, 1.4],
        "hitbox_type": "any-touch", # phase through,
        "collide_effect": "neg-gravity",
        "requires_click": False, # if player needs to click to activate,
        "temp_symbol": 'yg'
    }
    blue_grav_portal = {
        "name": "reverse_grav_portal",
        "hitbox_xrange": [0.1, 0.9],
        "hitbox_yrange": [-1.4, 1.4],
        "hitbox_type": "any-touch", # phase through,
        "collide_effect": "pos-gravity",
        "requires_click": False, # if player needs to click to activate
        "temp_symbol": 'bg'
    }

class LevelObject:
    """
    Represents a single object in a level. object types must be found in the `engine.objects.OBJECTS` dict.
    These should be created on level load, and NOT on every tick.
    
    Contains other data such as has_been_activated, position, (in the future, group, color, etc.)
    """
    def __init__(self, obj_dict: dict, posx: float, posy: float):
        # assert obj_dict["name"] in OBJECTS.__dict__.keys(), f"Object type {obj_dict['name']} not found in OBJECTS dict."
        self.data = deepcopy(obj_dict)
        
        self.x = posx
        self.y = posy
        self.has_been_activated = False

    def __str__(self) -> str:
        if self.data:
            return f"LevelObject<{self.data.get('name')}>(x={self.x},y={self.y})"
        return f"(Empty) LevelObject(x={self.x},y={self.y})"
        
    def __getitem__(self, key):
        return self.data[key]