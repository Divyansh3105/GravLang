<div align="center">
  <h1>GravLang</h1>
  <p><strong>A lightweight, multi-paradigm dynamic programming language with an AST interpreter & custom IDE.</strong></p>

[![Python Version](https://img.shields.io/badge/python-3.8+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-285%20passed-success.svg?style=flat)]()
[![Type Checked](https://img.shields.io/badge/pyright-clean-blue.svg?style=flat)]()
[![License](https://img.shields.io/badge/license-MIT-green.svg?style=flat)](LICENSE)

</div>

<br />

**GravLang** is an interpreted, dynamically-typed programming language written entirely in Python. It features an expressive syntax blending Python's readability with structured C-style blocks, a full object-oriented model, closures, exception handling, string interpolation, and an opinionated code formatter.

It includes both a command-line interpreter and a feature-rich, themeable **GUI IDE** with step debugging, compiler stage visualization, live diagnostics, and built-in interactive demo applications.

---

## 📑 Table of Contents

- [✨ Key Features](#-key-features)
- [💻 Interactive IDE Features](#-interactive-ide-features)
- [🎮 Built-in Interactive Demos](#-built-in-interactive-demos)
- [🚀 Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
- [📖 Usage & Commands](#-usage--commands)
  - [Running the IDE](#running-the-ide)
  - [Headless Execution](#headless-execution)
  - [Running the Code Formatter](#running-the-code-formatter)
  - [Running Tests](#running-tests)
- [📝 Language Syntax Overview](#-language-syntax-overview)
- [🧩 Architecture](#-architecture)
- [📖 Documentation](#-documentation)
- [📜 License](#-license)

---

## ✨ Key Features

- **Multi-Paradigm Engine:** Procedural, functional (closures, lambdas), and object-oriented programming.
- **Object-Oriented System:** Native classes, inheritance (`class Child extends Parent`), constructors (`init`), methods, overriding, and `self` references.
- **Control Flow & Loops:** `if / elif / else`, `while / else / finally`, standard `for` loops, and collection iteration with `for (item in collection)`. Fully supports `break` and `continue`.
- **First-Class Functions & Closures:** Higher-order functions, anonymous arrow syntax `(x, y) => x + y`, closures, and variadic rest parameters (`...rest`).
- **Data Structures & Slicing:**
  - **Strings:** Double-quoted strings, slicing (`str[1:4]`, `str[2:]`, `str[:3]`), concatenation, indexing.
  - **F-Strings:** Native string interpolation (`f"Hello {name}, total: {a + b}"`).
  - **Arrays:** Literal `[1, 2, 3]`, array slicing, methods (`push`, `pop`, `len`, `sort`, `reverse`, `contains`).
  - **Dictionaries:** Literal `{"key": "value"}`, `.keys()`, `.values()`, `del dict[key]` deletion.
- **Exception Handling:** Robust `try / catch (e) / finally` blocks with custom user error throwing (`throw "error message"`).
- **Code Formatter:** Built-in canonical code formatter (`format_source`, `format_file`) enforcing consistent indentation, operator spacing, and minimal parenthesis usage.

---

## 💻 Interactive IDE Features

GravLang includes a custom GUI IDE built with Tkinter:

- **Themeable Interface:** Multiple themes including Catppuccin Mocha, Macchiato, Frappé, Latte, Dark, and Light.
- **Multi-Tab Editor:** Tabbed interface with syntax highlighting, auto-completion popups, line numbering, code folding, and gutter breakpoints.
- **Compiler Stages Visualizer:** Real-time side-by-side inspection pipeline:
  - **Lexer Tokens:** Token stream viewer.
  - **Parser AST:** Hierarchical Abstract Syntax Tree representation.
  - **Interpreter Trace:** Live execution step-by-step event trace log.
- **Integrated Debugger & Inspector:** Breakpoint toggling, single-step execution, and live variable scope inspection panel.
- **Live Diagnostics & Linter:** Real-time error detection tooltip and clickable Problems panel for instant line navigation.
- **Find & Replace:** Search bar supporting keyboard shortcuts (`Ctrl+F`, `Ctrl+H`).

---

## 🎮 Built-in Interactive Demos

The IDE includes several ready-to-run demo applications located in `demos/`:

- 🐍 **Snake Game** (`demos/snake_game.grav`): Grid-based game implementation demonstrating loops, state arrays, and condition logic.
- 📝 **Todo App** (`demos/todo_app.grav`): Task management application showcasing classes, array operations, and user input handling.
- 🧠 **Brainfuck Interpreter** (`demos/brainfuck.grav`): Esoteric programming language interpreter implemented entirely in GravLang.
- 📊 **Grade Analyzer** (`demos/grade_analyzer.grav`): Comprehensive data processing application utilizing dictionary maps, sorting algorithms, and formatting.

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.8+** (Python 3.10+ recommended)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Divyansh3105/GravLang.git
   cd GravLang
   ```

2. **(Optional) Create a virtual environment:**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Linux/macOS:
   source venv/bin/activate
   ```

3. **Install dependencies (or install in editable mode):**
   ```bash
   pip install -e .
   ```

---

## 📖 Usage & Commands

### Running the IDE

Launch the GravLang GUI IDE:
```bash
python main.py
# Or via CLI entrypoint if installed:
gravlang-ide
```

### Headless Execution

Execute a `.grav` source file directly from the terminal:
```bash
python main.py demos/snake_game.grav
# Or via CLI entrypoint:
gravlang demos/snake_game.grav
```

### Running the Code Formatter

Format GravLang code files directly:
```bash
python -m gravlang.core.formatter demos/todo_app.grav
```

### Running Tests

Run the complete test suite (285 tests):
```bash
pytest
```

---

## 📝 Language Syntax Overview

```gravlang
// Classes & Inheritance
class Person {
    func init(name, age) {
        self.name = name;
        self.age = age;
    }

    func greet() {
        return f"Hello, I am {self.name} and I am {self.age} years old.";
    }
}

class Student extends Person {
    func init(name, age, grade) {
        super.init(name, age);
        self.grade = grade;
    }
}

// Function with Variadic Args & Lambda
func calculateTotal(multiplier, ...nums) {
    let sum = 0;
    for (n in nums) {
        sum += n;
    }
    return sum * multiplier;
}

let applyOp = (a, b) => a + b;

// Main Logic & Error Handling
try {
    let p = new Student("Alice", 20, "A+");
    print(p.greet());

    let numbers = [10, 20, 30, 40];
    let slice = numbers[1:3]; // [20, 30]

    print(f"Total: {calculateTotal(2, 5, 10, 15)}");
} catch (err) {
    print(f"Caught error: {err}");
} finally {
    print("Execution complete.");
}
```

---

## 🧩 Architecture

GravLang follows a clean, modular pipeline:

- **Lexer ([`gravlang/core/lexer.py`](file:///d:/Projects/GravLang/gravlang/core/lexer.py)):** Converts raw source code into token sequences.
- **Parser ([`gravlang/core/parser.py`](file:///d:/Projects/GravLang/gravlang/core/parser.py)):** Parses tokens into AST node objects ([`ast_nodes.py`](file:///d:/Projects/GravLang/gravlang/core/ast_nodes.py)).
- **Interpreter ([`gravlang/core/interpreter.py`](file:///d:/Projects/GravLang/gravlang/core/interpreter.py)):** Evaluates AST nodes within scoped environment frames ([`environment.py`](file:///d:/Projects/GravLang/gravlang/core/environment.py)).
- **Formatter ([`gravlang/core/formatter.py`](file:///d:/Projects/GravLang/gravlang/core/formatter.py)):** Converts AST nodes back into clean, canonical GravLang code.
- **IDE Subsystem ([`gravlang/ide/`](file:///d:/Projects/GravLang/gravlang/ide)):** Modular Tkinter GUI application providing editor tabs, bottom panel diagnostics, variable inspector, and compiler pipeline views.

---

## 📖 Documentation

Full documentation and syntax guides are available on the **[GravLang Docs Site](https://divyansh3105.github.io/GravLang/)** (built using MkDocs Material).

To view documentation locally:
```bash
pip install mkdocs-material
mkdocs serve
```

---

## 📜 License

This project is licensed under the [MIT License](LICENSE).
