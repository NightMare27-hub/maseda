import pytest
from snake import Direction, SnakeGame


def test_initial_state():
    game = SnakeGame(width=10, height=10, initial_length=3, seed=42)
    assert game.width == 10
    assert game.height == 10
    assert len(game.snake) == 3
    assert game.score == 0
    assert not game.game_over
    assert not game.won
    assert game.direction == Direction.RIGHT
    assert game.head == (5, 5)
    assert game.snake == [(5, 5), (4, 5), (3, 5)]
    assert game.food is not None
    assert game.food not in game.snake


def test_invalid_parameters():
    with pytest.raises(ValueError):
        SnakeGame(width=2, height=5)
    with pytest.raises(ValueError):
        SnakeGame(width=5, height=2)
    with pytest.raises(ValueError):
        SnakeGame(width=5, height=5, initial_length=0)
    with pytest.raises(ValueError):
        SnakeGame(width=5, height=5, initial_length=6)


def test_movement():
    game = SnakeGame(width=10, height=10, initial_length=3)
    game.food = (0, 0)  # Move food out of immediate path
    head_before = game.head

    active = game.step()
    assert active is True
    assert game.head == (head_before[0] + 1, head_before[1])
    assert len(game.snake) == 3
    assert game.snake[1] == head_before


def test_direction_changes():
    game = SnakeGame(width=10, height=10, initial_length=3)
    game.food = (0, 0)

    # Disallow 180-degree turn
    assert game.direction == Direction.RIGHT
    assert not game.change_direction(Direction.LEFT)
    assert game.next_direction == Direction.RIGHT

    # Allow 90-degree turn
    assert game.change_direction(Direction.DOWN)
    assert game.next_direction == Direction.DOWN
    game.step()
    assert game.direction == Direction.DOWN
    assert game.head == (5, 6)

    # Turn LEFT
    assert game.change_direction(Direction.LEFT)
    game.step()
    assert game.direction == Direction.LEFT
    assert game.head == (4, 6)

    # Turn UP
    assert game.change_direction(Direction.UP)
    game.step()
    assert game.direction == Direction.UP
    assert game.head == (4, 5)


def test_eat_food_and_grow():
    game = SnakeGame(width=10, height=10, initial_length=3)
    # Place food directly in front of snake
    game.food = (game.head[0] + 1, game.head[1])
    initial_length = len(game.snake)
    food_pos = game.food

    active = game.step()
    assert active is True
    assert game.head == food_pos
    assert len(game.snake) == initial_length + 1
    assert game.score == 1
    assert game.food != food_pos
    assert game.food not in game.snake


def test_wall_collision():
    game = SnakeGame(width=6, height=6, initial_length=3)
    game.food = (0, 0)
    # Snake starts at [(3, 3), (2, 3), (1, 3)], moving RIGHT
    # Step 1: head to (4, 3)
    game.step()
    assert not game.game_over
    # Step 2: head to (5, 3)
    game.step()
    assert not game.game_over
    # Step 3: wall collision at x=6
    active = game.step()
    assert active is False
    assert game.game_over is True


def test_self_collision():
    game = SnakeGame(width=10, height=10, initial_length=5)
    # Start at [(5, 5), (4, 5), (3, 5), (2, 5), (1, 5)]
    game.food = (0, 0)
    # Turn UP -> (5, 4)
    game.change_direction(Direction.UP)
    game.step()
    # Turn LEFT -> (4, 4)
    game.change_direction(Direction.LEFT)
    game.step()
    # Turn DOWN -> (4, 5) which is occupied by body
    game.change_direction(Direction.DOWN)
    active = game.step()
    assert active is False
    assert game.game_over is True


def test_tail_chase_no_collision_when_not_eating():
    # If snake head moves into the spot currently occupied by the tail,
    # and no food is eaten, tail moves out of the way safely.
    game = SnakeGame(width=10, height=10, initial_length=4)
    # Head is (5, 5), tail is (2, 5)
    # Loop around to tail
    game.food = (0, 0)
    game.change_direction(Direction.UP)    # (5, 4)
    game.step()
    game.change_direction(Direction.LEFT)  # (4, 4)
    game.step()
    game.change_direction(Direction.DOWN)  # (4, 5) - safe because body advanced
    active = game.step()
    assert active is True
    assert not game.game_over


def test_win_condition_full_grid():
    # 3x3 grid = 9 cells, start with 3 cells
    game = SnakeGame(width=3, height=3, initial_length=3)
    # Fill snake manually to test victory upon final food spawn
    game.snake = [(0, 0), (1, 0), (2, 0), (2, 1), (1, 1), (0, 1), (0, 2), (1, 2)]
    # Remaining cell is (2, 2)
    food = game.spawn_food()
    assert food == (2, 2)
    assert not game.won

    # Add the remaining cell into snake
    game.snake.insert(0, (2, 2))
    food = game.spawn_food()
    assert food is None
    assert game.won is True
    assert game.game_over is True


def test_render_ascii():
    game = SnakeGame(width=5, height=5, initial_length=2)
    rendered = game.render_ascii()
    assert "+" in rendered
    assert "O" in rendered  # head
    assert "o" in rendered  # body
    assert "*" in rendered  # food
    lines = rendered.splitlines()
    assert len(lines) == 7  # 5 rows + top/bottom borders
    assert all(len(line) == 7 for line in lines)  # 5 cols + left/right borders


def test_step_after_game_over():
    game = SnakeGame(width=4, height=4, initial_length=2)
    game.game_over = True
    assert game.step() is False
    assert game.change_direction(Direction.UP) is False
