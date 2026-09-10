"""Minimal escape-room game logic."""

WORLD = {
    "study": {
        "description": "A dusty study with a portrait dated 1894 and a locked desk.",
        "exits": {"north": "hallway"},
    },
    "hallway": {
        "description": "A hallway with a locked cellar door.",
        "exits": {"south": "study", "down": "cellar"},
    },
    "cellar": {
        "description": "You found the exit. You escaped!",
        "exits": {},
    },
}


class EscapeRoomGame:
    def __init__(self):
        self.reset()

    def reset(self):
        self.room = "study"
        self.inventory = []
        self.desk_open = False
        self.cellar_open = False
        return self.look()

    def look(self):
        return {
            "room": self.room,
            "description": WORLD[self.room]["description"],
            "exits": list(WORLD[self.room]["exits"]),
        }

    def inspect(self, object_name):
        objects = {
            "study": {
                "portrait": "The portrait is dated 1894.",
                "desk": "The desk has a four-digit keypad.",
            },
            "hallway": {
                "cellar door": "The cellar door has a silver keyhole.",
            },
        }
        return objects.get(self.room, {}).get(
            object_name.lower(), "You find nothing interesting."
        )

    def enter_code(self, target, code):
        if target.lower() != "desk":
            return f"The {target} does not have a keypad."
        if self.room == "study" and code == "1894":
            self.desk_open = True
            return "The desk opens. Inside is a silver key."
        return "Nothing happens."

    def take(self, item_name):
        if item_name.lower() != "silver key":
            return f"You cannot take the {item_name}."
        if not self.desk_open or "silver key" in self.inventory:
            return "There is no key to take."

        self.inventory.append("silver key")
        return "You take the silver key."

    def use(self, item_name, target):
        if (
            item_name.lower() == "silver key"
            and target.lower() == "cellar door"
            and self.room == "hallway"
            and "silver key" in self.inventory
        ):
            self.cellar_open = True
            return "The cellar door unlocks."
        return f"You cannot use the {item_name} on the {target}."

    def move(self, direction):
        destination = WORLD[self.room]["exits"].get(direction)
        if destination is None:
            return "You cannot go that way."
        if destination == "cellar" and not self.cellar_open:
            return "The cellar door is locked."

        self.room = destination
        return self.look()

    def status(self):
        return {
            "room": self.room,
            "inventory": self.inventory,
            "escaped": self.room == "cellar",
        }

    def get_hint(self):
        hints = {
            "study": "Inspect the portrait and the desk.",
            "hallway": "The cellar door needs an item from the study.",
            "cellar": "You have already escaped.",
        }
        return hints[self.room]
