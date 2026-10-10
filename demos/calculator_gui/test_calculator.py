"""
Automated unit test suite for the Calculator application.

Verifies CalculatorEngine logic headless in pytest:
- Basic arithmetic: addition, subtraction, multiplication, division
- Operator precedence and parentheses
- Running calculations and chaining operations
- Floating point and integer representations
- Division by zero and invalid expression error recovery
- Backspace, sign toggling, and clear operations
"""

import pytest
from calculator import CalculatorEngine


def test_basic_arithmetic():
    engine = CalculatorEngine()
    success, result = engine.evaluate("3 + 5")
    assert success is True
    assert result == "8"

    success, result = engine.evaluate("10 - 4")
    assert success is True
    assert result == "6"

    success, result = engine.evaluate("6 * 7")
    assert success is True
    assert result == "42"

    success, result = engine.evaluate("20 / 4")
    assert success is True
    assert result == "5"


def test_order_of_operations():
    engine = CalculatorEngine()
    success, result = engine.evaluate("2 + 3 * 4")
    assert success is True
    assert result == "14"

    success, result = engine.evaluate("(2 + 3) * 4")
    assert success is True
    assert result == "20"

    success, result = engine.evaluate("100 - 20 / 4 * 2")
    assert success is True
    assert result == "90"


def test_decimal_and_negative_numbers():
    engine = CalculatorEngine()
    success, result = engine.evaluate("0.1 + 0.2")
    assert success is True
    assert float(result) == pytest.approx(0.3)

    success, result = engine.evaluate("-5 + 12")
    assert success is True
    assert result == "7"

    success, result = engine.evaluate("-8 * -3")
    assert success is True
    assert result == "24"


def test_division_by_zero():
    engine = CalculatorEngine()
    success, result = engine.evaluate("15 / 0")
    assert success is False
    assert "Division by zero" in result
    assert engine.error_state is True


def test_invalid_expressions_graceful_recovery():
    engine = CalculatorEngine()
    # Incomplete expression
    success, result = engine.evaluate("5 +")
    assert success is False
    assert "Invalid expression" in result

    # Unmatched parenthesis
    success, result = engine.evaluate("(2 + 3")
    assert success is False
    assert "Invalid expression" in result

    # Typing after an error recovers cleanly
    engine.input_char("9")
    assert engine.error_state is False
    assert engine.expression == "9"


def test_running_calculations_chaining():
    engine = CalculatorEngine()
    # Evaluate first expression: 5 * 4 = 20
    engine.input_char("5")
    engine.input_char("*")
    engine.input_char("4")
    success, result = engine.evaluate()
    assert success is True
    assert result == "20"
    assert engine.last_result == 20

    # Pressing an operator immediately continues running calculation
    engine.input_char("+")
    engine.input_char("10")
    assert engine.expression == "20+10"
    success, result = engine.evaluate()
    assert success is True
    assert result == "30"


def test_fresh_input_after_evaluation():
    engine = CalculatorEngine()
    engine.input_char("8")
    engine.input_char("+")
    engine.input_char("2")
    engine.evaluate()
    assert engine.just_evaluated is True

    # Pressing a digit starts a fresh calculation
    engine.input_char("7")
    assert engine.just_evaluated is False
    assert engine.expression == "7"


def test_ans_variable_support():
    engine = CalculatorEngine()
    engine.evaluate("25 + 25")
    assert engine.last_result == 50

    success, result = engine.evaluate("ans * 2")
    assert success is True
    assert result == "100"


def test_backspace_and_clear():
    engine = CalculatorEngine()
    engine.input_char("1")
    engine.input_char("2")
    engine.input_char("3")
    assert engine.expression == "123"

    engine.backspace()
    assert engine.expression == "12"

    engine.clear()
    assert engine.expression == ""

    # Test clear_all
    engine.evaluate("4 + 4")
    assert engine.last_result == 8
    engine.clear_all()
    assert engine.expression == ""
    assert engine.last_result is None
    assert engine.history_text == ""


def test_toggle_sign():
    engine = CalculatorEngine()
    engine.input_char("42")
    engine.toggle_sign()
    assert engine.expression == "-(42)"

    engine.toggle_sign()
    assert engine.expression == "42"

    # Toggle sign on evaluated result
    engine.evaluate()
    engine.toggle_sign()
    assert engine.expression == "-42"
