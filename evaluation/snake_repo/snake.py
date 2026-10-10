import random
import time
import sys
import os
from enum import Enum
from typing import Any, List, Optional, Tuple

try:
    import curses
except ImportError:
    curses = None  # type: ignore

if sys.platform == "win32":
    try:
        import msvcrt
    except ImportError:
        msvcrt = None
else:
    msvcrt = None


class Direction(Enum):
    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

    @property
    def opposite(self) -> "Direction":
        opposites = {
            Direction.UP: Direction.DOWN,
            Direction.DOWN: Direction.UP,
            Direction.LEFT: Direction.RIGHT,
            Direction.RIGHT: Direction.LEFT,
        }
        return opposites[self]


class SnakeGame:
    """Headless Snake game engine."""

    def __init__(
        self, 
        width: int = 20, 
        height: int = 20, 
        initial_length: int = 3, 
        seed: Optional[int] = None
    ):
        if width < 3 or height < 3:
            raise ValueError("Grid width and height must be at least 3.")
        if initial_length < 1 or initial_length > width:
            raise ValueError("Initial length must be between 1 and grid width.")

        self.width = width
        self.height = height
        self.random = random.Random(seed)

        self.direction = Direction.RIGHT
        self.next_direction = Direction.RIGHT
        self.score = 0
        self.game_over = False
        self.won = False

        start_y = height // 2
        start_x = width // 2
        self.snake: List[Tuple[int, int]] = [
            (start_x - i, start_y) for i in range(initial_length)
        ]

        self.food: Optional[Tuple[int, int]] = None
        self.spawn_food()

    @property
    def head(self) -> Tuple[int, int]:
        return self.snake[0]

    def change_direction(self, new_direction: Direction) -> bool:
        """Change the snake's direction, disallowing 180-degree turns."""
        if self.game_over:
            return False
        if new_direction != self.direction.opposite:
            self.next_direction = new_direction
            return True
        return False

    def spawn_food(self) -> Optional[Tuple[int, int]]:
        """Spawn food at a random unoccupied cell."""
        occupied = set(self.snake)
        empty_cells = [
            (x, y)
            for y in range(self.height)
            for x in range(self.width)
            if (x, y) not in occupied
        ]
        if not empty_cells:
            self.food = None
            self.won = True
            self.game_over = True
            return None

        self.food = self.random.choice(empty_cells)
        return self.food

    def step(self) -> bool:
        """Advance the game by one tick.

        Returns True if game is still active, False if game is over.
        """
        if self.game_over:
            return False

        self.direction = self.next_direction
        dx, dy = self.direction.value
        head_x, head_y = self.head
        new_head = (head_x + dx, head_y + dy)
        new_x, new_y = new_head

        # Wall collision
        if not (0 <= new_x < self.width and 0 <= new_y < self.height):
            self.game_over = True
            return False

        # Check eating food
        eating = self.food is not None and new_head == self.food

        # Self collision: if not eating, tail moves forward, so colliding with tail is safe.
        # If eating, tail stays, so entire current snake body is an obstacle.
        body_to_check = self.snake if eating else self.snake[:-1]
        if new_head in body_to_check:
            self.game_over = True
            return False

        self.snake.insert(0, new_head)
        if eating:
            self.score += 1
            self.spawn_food()
        else:
            self.snake.pop()

        return not self.game_over

    def render_ascii(self) -> str:
        """Return an ASCII representation of the current board state."""
        grid = [[" " for _ in range(self.width)] for _ in range(self.height)]
        if self.food is not None:
            fx, fy = self.food
            grid[fy][fx] = "*"

        for idx, (sx, sy) in enumerate(self.snake):
            grid[sy][sx] = "O" if idx == 0 else "o"

        border = "+" + "-" * self.width + "+"
        lines = [border]
        for row in grid:
            lines.append("|" + "".join(row) + "|")
        lines.append(border)
        return "\n".join(lines)


def run_curses(stdscr: Any) -> None:
    """Run an interactive curses session for playing the game."""
    if curses is None:
        raise RuntimeError("curses is not available on this platform.")

    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(120)

    game = SnakeGame(width=20, height=20)

    key_mapping = {
        curses.KEY_UP: Direction.UP,
        curses.KEY_DOWN: Direction.DOWN,
        curses.KEY_LEFT: Direction.LEFT,
        curses.KEY_RIGHT: Direction.RIGHT,
        ord("w"): Direction.UP,
        ord("s"): Direction.DOWN,
        ord("a"): Direction.LEFT,
        ord("d"): Direction.RIGHT,
    }

    while not game.game_over:
        stdscr.clear()
        stdscr.addstr(0, 0, f"Score: {game.score} | Press 'q' to quit")

        # Draw frame and board
        ascii_board = game.render_ascii()
        for i, line in enumerate(ascii_board.split("\n")):
            stdscr.addstr(i + 1, 0, line)
        stdscr.refresh()

        try:
            key = stdscr.getch()
        except Exception:
            key = -1

        if key in (ord("q"), ord("Q")):
            break
        if key in key_mapping:
            game.change_direction(key_mapping[key])

        game.step()

    stdscr.clear()
    if game.won:
        stdscr.addstr(2, 2, f"Congratulations! You won with score: {game.score}!")
    else:
        stdscr.addstr(2, 2, f"Game Over! Final Score: {game.score}")
    stdscr.addstr(4, 2, "Press any key to exit...")
    stdscr.nodelay(False)
    stdscr.refresh()
    stdscr.getch()


def run_msvcrt() -> None:
    """Run an interactive session using Windows msvcrt without curses."""
    game = SnakeGame(width=20, height=20)
    
    # Clear screen and hide cursor (ANSI escape sequence)
    print("\033[2J\033[H\033[?25l", end="")
    
    try:
        last_tick = time.time()
        tick_interval = 0.12

        while not game.game_over:
            # Non-blocking key check
            if msvcrt and msvcrt.kbhit():
                ch = msvcrt.getch()
                if ch in (b'\x00', b'\xe0'):  # Special key prefix on Windows
                    ch2 = msvcrt.getch()
                    if ch2 == b'H':  # Up arrow
                        game.change_direction(Direction.UP)
                    elif ch2 == b'P':  # Down arrow
                        game.change_direction(Direction.DOWN)
                    elif ch2 == b'K':  # Left arrow
                        game.change_direction(Direction.LEFT)
                    elif ch2 == b'M':  # Right arrow
                        game.change_direction(Direction.RIGHT)
                else:
                    try:
                        char_str = ch.decode('utf-8').lower()
                    except Exception:
                        char_str = ""
                    
                    if char_str == 'q':
                        break
                    elif char_str == 'w':
                        game.change_direction(Direction.UP)
                    elif char_str == 's':
                        game.change_direction(Direction.DOWN)
                    elif char_str == 'a':
                        game.change_direction(Direction.LEFT)
                    elif char_str == 'd':
                        game.change_direction(Direction.RIGHT)

            now = time.time()
            if now - last_tick >= tick_interval:
                game.step()
                last_tick = now

            # Move cursor to top-left and redraw
            output = f"\033[HScore: {game.score} | Use WASD or Arrows, 'q' to quit\n" + game.render_ascii() + "\n"
            sys.stdout.write(output)
            sys.stdout.flush()

            time.sleep(0.01)

    finally:
        # Restore cursor
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()

    print()
    if game.won:
        print(f"Congratulations! You won with score: {game.score}!")
    else:
        print(f"Game Over! Final Score: {game.score}")


def main() -> None:
    if sys.platform == "win32" and msvcrt is not None:
        try:
            run_msvcrt()
            return
        except Exception as e:
            print(f"Could not start Windows msvcrt interface: {e}")

    if curses is not None:
        try:
            curses.wrapper(run_curses)
            return
        except Exception as e:
            print(f"Could not start curses interface: {e}")
    else:
        print("Curses and msvcrt not available or usable.")

    print("Running headless demonstration:")
    game = SnakeGame(width=10, height=10)
    print(game.render_ascii())


if __name__ == "__main__":
    main()
