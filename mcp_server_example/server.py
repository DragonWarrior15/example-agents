"""MCP server for the escape-room game."""

from mcp.server.fastmcp import FastMCP

from game import EscapeRoomGame


mcp = FastMCP("Game Server")
game = EscapeRoomGame()


@mcp.tool()
def start_game() -> dict:
    """Start a new game and return the initial room."""
    return game.reset()


@mcp.tool()
def look() -> dict:
    """Look around the current room."""
    return game.look()


@mcp.tool()
def inspect(object_name: str) -> str:
    """Inspect an object in the current room for clues."""
    return game.inspect(object_name)


@mcp.tool()
def move(direction: str) -> dict | str:
    """Move north, south, or down from the current room."""
    return game.move(direction)


@mcp.tool()
def take(item_name: str) -> str:
    """Take an item that you have discovered."""
    return game.take(item_name)


@mcp.tool()
def use(item_name: str, target: str) -> str:
    """Use an inventory item on an object in the room."""
    return game.use(item_name, target)


@mcp.tool()
def enter_code(target: str, code: str) -> str:
    """Enter a code into an object with a keypad."""
    return game.enter_code(target, code)


@mcp.tool()
def ask_for_hint() -> str:
    """Get a hint for the current room."""
    return game.get_hint()


@mcp.resource("game://status")
def game_status() -> dict:
    """Return the current room, inventory, and completion state."""
    return game.status()


@mcp.prompt()
def play_escape_room() -> str:
    """Provide instructions to an agent playing the game."""
    return (
        "Escape from the room using the available game tools. "
        "Look around, inspect objects, collect useful items, and avoid guessing."
    )


if __name__ == "__main__":
    mcp.run()
