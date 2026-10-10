"""
Modern Desktop Calculator Application

Dual-contract architecture:
- CalculatorEngine: Pure mathematical logic with safe AST evaluation,
  running calculation support, history tracking, and graceful error handling.
- CalculatorApp: Polished modern desktop GUI built with tkinter.ttk featuring
  a responsive grid layout, customized styling, and comprehensive keyboard bindings.
"""

import ast
import operator
import tkinter as tk
from tkinter import ttk
from typing import Optional, Tuple, Union


class CalculatorEngine:
    """Pure computational engine for expression evaluation and state management."""

    # Allowed binary operators mapped to their operator implementations
    SAFE_BIN_OPS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
    }

    # Allowed unary operators
    SAFE_UNARY_OPS = {
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
    }

    def __init__(self) -> None:
        self.expression: str = ""
        self.last_result: Optional[Union[int, float]] = None
        self.history_text: str = ""
        self.just_evaluated: bool = False
        self.error_state: bool = False

    def input_char(self, char: str) -> None:
        """Append a character to the current expression, handling running state."""
        if self.error_state:
            self.clear()

        # If user starts typing right after evaluation:
        # - If an operator is pressed, continue running calculation with last result
        # - If a digit, parenthesis, or decimal is pressed, start a fresh expression
        if self.just_evaluated:
            self.just_evaluated = False
            if char in "+-*/%^":
                if self.last_result is not None:
                    formatted_prev = self._format_number(self.last_result)
                    self.expression = f"{formatted_prev}{char}"
                    return
            else:
                self.expression = ""

        # Replace '^' with '**' when evaluating, but allow '^' in display
        self.expression += char

    def backspace(self) -> None:
        """Remove the last character in the current expression."""
        if self.error_state or self.just_evaluated:
            self.clear()
            return
        if self.expression:
            self.expression = self.expression[:-1]

    def clear(self) -> None:
        """Clear current expression and error state."""
        self.expression = ""
        self.error_state = False
        self.just_evaluated = False

    def clear_all(self) -> None:
        """Clear expression, history, and stored result."""
        self.clear()
        self.last_result = None
        self.history_text = ""

    def toggle_sign(self) -> None:
        """Negate the entire expression or current number."""
        if self.error_state:
            self.clear()
            return

        if self.just_evaluated and self.last_result is not None:
            self.expression = str(-self.last_result)
            self.just_evaluated = False
            return

        expr = self.expression.strip()
        if not expr:
            return

        if expr.startswith("-(") and expr.endswith(")"):
            self.expression = expr[2:-1]
        elif expr.startswith("-"):
            self.expression = expr[1:]
        else:
            self.expression = f"-({expr})"

    def evaluate(self, expr: Optional[str] = None) -> Tuple[bool, str]:
        """Safe evaluation of mathematical expression using AST parsing."""
        target_expr = expr if expr is not None else self.expression
        target_expr = target_expr.strip()

        if not target_expr:
            return True, "0"

        # Normalize operators: handle display symbols
        normalized = target_expr.replace("×", "*").replace("÷", "/").replace("^", "**")

        try:
            node = ast.parse(normalized, mode="eval")
            val = self._eval_ast_node(node.body)

            # Check for invalid float values
            if isinstance(val, (int, float)):
                formatted = self._format_number(val)
                self.last_result = val
                self.history_text = f"{target_expr} = {formatted}"
                self.expression = formatted
                self.just_evaluated = True
                self.error_state = False
                return True, formatted
            else:
                self.error_state = True
                return False, "Error: Invalid expression"

        except ZeroDivisionError:
            self.error_state = True
            return False, "Error: Division by zero"
        except (SyntaxError, ValueError, TypeError):
            self.error_state = True
            return False, "Error: Invalid expression"
        except OverflowError:
            self.error_state = True
            return False, "Error: Overflow"
        except Exception:
            self.error_state = True
            return False, "Error: Calculation failed"

    def _eval_ast_node(self, node: ast.AST) -> Union[int, float]:
        """Recursively evaluate approved AST nodes only (safe sandbox)."""
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError("Non-numeric constant")

        # Python <3.8 compatibility
        if hasattr(ast, "Num") and isinstance(node, getattr(ast, "Num")):
            return node.n

        if isinstance(node, ast.Name):
            if node.id.lower() == "ans":
                if self.last_result is not None:
                    return self.last_result
                return 0
            raise ValueError(f"Unknown variable: {node.id}")

        if isinstance(node, ast.BinOp):
            left_val = self._eval_ast_node(node.left)
            right_val = self._eval_ast_node(node.right)
            op_type = type(node.op)
            if op_type in self.SAFE_BIN_OPS:
                # Avoid excessive power blowups
                if op_type is ast.Pow and (abs(right_val) > 1000 or abs(left_val) > 1e10):
                    raise OverflowError("Exponent too large")
                return self.SAFE_BIN_OPS[op_type](left_val, right_val)
            raise ValueError(f"Unsupported binary operator: {op_type}")

        if isinstance(node, ast.UnaryOp):
            operand_val = self._eval_ast_node(node.operand)
            op_type = type(node.op)
            if op_type in self.SAFE_UNARY_OPS:
                return self.SAFE_UNARY_OPS[op_type](operand_val)
            raise ValueError(f"Unsupported unary operator: {op_type}")

        raise ValueError(f"Unsupported AST expression node: {type(node)}")

    @staticmethod
    def _format_number(val: Union[int, float]) -> str:
        """Cleanly format a number, eliminating trailing zeros from whole floats."""
        if isinstance(val, float):
            if val.is_integer():
                return str(int(val))
            # Round to eliminate precision noise
            rounded = round(val, 10)
            if rounded.is_integer():
                return str(int(rounded))
            return f"{rounded:g}"
        return str(val)


class CalculatorApp:
    """Tkinter TTK Desktop Application interface for the calculator."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Calculator")
        self.root.geometry("360x520")
        self.root.minsize(320, 460)

        self.engine = CalculatorEngine()

        self._setup_styles()
        self._create_widgets()
        self._bind_keys()
        self._update_display("0")

    def _setup_styles(self) -> None:
        """Configure modern ttk styling and color palette."""
        self.style = ttk.Style()
        available_themes = self.style.theme_names()
        if "clam" in available_themes:
            self.style.theme_use("clam")

        # Theme Palette
        bg_color = "#1e1e2e"
        display_bg = "#181825"
        btn_digit_bg = "#313244"
        btn_digit_fg = "#cdd6f4"
        btn_op_bg = "#45475a"
        btn_op_fg = "#89b4fa"
        btn_eq_bg = "#a6e3a1"
        btn_eq_fg = "#11111b"
        btn_action_bg = "#f38ba8"
        btn_action_fg = "#11111b"

        self.root.configure(bg=bg_color)

        self.style.configure("Main.TFrame", background=bg_color)
        self.style.configure(
            "Display.TFrame",
            background=display_bg,
            relief="flat",
        )

        # Button styles
        btn_font = ("Helvetica", 14, "bold")
        self.style.configure(
            "Digit.TButton",
            font=btn_font,
            background=btn_digit_bg,
            foreground=btn_digit_fg,
            borderwidth=0,
            focuscolor="none",
        )
        self.style.map("Digit.TButton", background=[("active", "#585b70")])

        self.style.configure(
            "Op.TButton",
            font=btn_font,
            background=btn_op_bg,
            foreground=btn_op_fg,
            borderwidth=0,
            focuscolor="none",
        )
        self.style.map("Op.TButton", background=[("active", "#6c7086")])

        self.style.configure(
            "Equal.TButton",
            font=btn_font,
            background=btn_eq_bg,
            foreground=btn_eq_fg,
            borderwidth=0,
            focuscolor="none",
        )
        self.style.map("Equal.TButton", background=[("active", "#94e2d5")])

        self.style.configure(
            "Action.TButton",
            font=btn_font,
            background=btn_action_bg,
            foreground=btn_action_fg,
            borderwidth=0,
            focuscolor="none",
        )
        self.style.map("Action.TButton", background=[("active", "#eba0ac")])

    def _create_widgets(self) -> None:
        """Build display and responsive button grid."""
        container = ttk.Frame(self.root, style="Main.TFrame", padding=12)
        container.pack(fill="both", expand=True)

        # Grid layout weights
        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)
        container.columnconfigure(2, weight=1)
        container.columnconfigure(3, weight=1)

        # Rows 0 & 1 for display, rows 2-6 for buttons
        container.rowconfigure(0, weight=1)
        container.rowconfigure(1, weight=2)
        for r in range(2, 7):
            container.rowconfigure(r, weight=2)

        # Display Screen Container
        disp_frame = ttk.Frame(container, style="Display.TFrame", padding=10)
        disp_frame.grid(row=0, column=0, columnspan=4, rowspan=2, sticky="nsew", pady=(0, 12))
        disp_frame.columnconfigure(0, weight=1)
        disp_frame.rowconfigure(0, weight=1)
        disp_frame.rowconfigure(1, weight=2)

        # History Label (Top, right-aligned, muted)
        self.history_label = tk.Label(
            disp_frame,
            text="",
            font=("Consolas", 11),
            fg="#a6adc8",
            bg="#181825",
            anchor="e",
        )
        self.history_label.grid(row=0, column=0, sticky="nsew")

        # Main Output Label (Large, right-aligned monospace)
        self.main_display = tk.Label(
            disp_frame,
            text="0",
            font=("Consolas", 26, "bold"),
            fg="#cdd6f4",
            bg="#181825",
            anchor="e",
        )
        self.main_display.grid(row=1, column=0, sticky="nsew")

        # Button Grid Definition: (text, row, col, style, callback)
        buttons = [
            ("C", 2, 0, "Action.TButton", self.on_clear),
            ("(", 2, 1, "Op.TButton", lambda: self.on_char("(")),
            (")", 2, 2, "Op.TButton", lambda: self.on_char(")")),
            ("/", 2, 3, "Op.TButton", lambda: self.on_char("/")),
            ("7", 3, 0, "Digit.TButton", lambda: self.on_char("7")),
            ("8", 3, 1, "Digit.TButton", lambda: self.on_char("8")),
            ("9", 3, 2, "Digit.TButton", lambda: self.on_char("9")),
            ("*", 3, 3, "Op.TButton", lambda: self.on_char("*")),
            ("4", 4, 0, "Digit.TButton", lambda: self.on_char("4")),
            ("5", 4, 1, "Digit.TButton", lambda: self.on_char("5")),
            ("6", 4, 2, "Digit.TButton", lambda: self.on_char("6")),
            ("-", 4, 3, "Op.TButton", lambda: self.on_char("-")),
            ("1", 5, 0, "Digit.TButton", lambda: self.on_char("1")),
            ("2", 5, 1, "Digit.TButton", lambda: self.on_char("2")),
            ("3", 5, 2, "Digit.TButton", lambda: self.on_char("3")),
            ("+", 5, 3, "Op.TButton", lambda: self.on_char("+")),
            ("⌫", 6, 0, "Action.TButton", self.on_backspace),
            ("0", 6, 1, "Digit.TButton", lambda: self.on_char("0")),
            (".", 6, 2, "Digit.TButton", lambda: self.on_char(".")),
            ("=", 6, 3, "Equal.TButton", self.on_evaluate),
        ]

        for text, r, c, style, cmd in buttons:
            btn = ttk.Button(container, text=text, style=style, command=cmd)
            btn.grid(row=r, column=c, padx=3, pady=3, sticky="nsew")

    def _bind_keys(self) -> None:
        """Bind keyboard shortcuts for evaluation, deletion, and operators."""
        self.root.bind("<Return>", lambda e: self.on_evaluate())
        self.root.bind("<KP_Enter>", lambda e: self.on_evaluate())
        self.root.bind("<BackSpace>", lambda e: self.on_backspace())
        self.root.bind("<Escape>", lambda e: self.on_clear())
        self.root.bind("<Delete>", lambda e: self.on_clear())

        # Standard printable characters for numbers, parentheses, and operations
        for char in "0123456789+-*/.()":
            self.root.bind(char, lambda e, c=char: self.on_char(c))
        self.root.bind("=", lambda e: self.on_evaluate())

    def on_char(self, char: str) -> None:
        """Handle character button press or keyboard input."""
        self.engine.input_char(char)
        self._update_display(self.engine.expression)

    def on_backspace(self) -> None:
        """Handle backspace button or key."""
        self.engine.backspace()
        self._update_display(self.engine.expression if self.engine.expression else "0")

    def on_clear(self) -> None:
        """Handle clear button or Escape key."""
        self.engine.clear()
        self._update_display("0")

    def on_evaluate(self) -> None:
        """Evaluate the current expression."""
        if not self.engine.expression and not self.engine.last_result:
            return

        success, message = self.engine.evaluate()
        if success:
            self.history_label.config(text=self.engine.history_text)
            self.main_display.config(fg="#a6e3a1")  # Accent green on success
            self._update_display(message)
        else:
            self.main_display.config(fg="#f38ba8")  # Red on error
            self._update_display(message)

    def _update_display(self, text: str) -> None:
        """Update main label display and reset default color if not in error."""
        if not self.engine.error_state and not self.engine.just_evaluated:
            self.main_display.config(fg="#cdd6f4")
        self.main_display.config(text=text if text else "0")
        self.history_label.config(text=self.engine.history_text)


def launch() -> None:
    """Operational entry point for GUI execution."""
    root = tk.Tk()
    app = CalculatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    launch()
