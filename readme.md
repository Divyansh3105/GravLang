<div align="center">
  <h1>🌌 GravLang</h1>
  <p><strong>A lightweight, elegantly designed programming language with a built-in Python interpreter and IDE.</strong></p>

[![Python version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Language Details](https://img.shields.io/badge/paradigm-multi--paradigm-brightgreen.svg)]()
[![License](https://img.shields.io/badge/license-MIT-blue.svg)]()

</div>

<br />

**GravLang** is an interpreted, dynamically-typed programming language written entirely in Python. Designed for simplicity and expressiveness, it offers a clean syntax that bridges the gap between Python's readability and C-style structured code.

Whether you execute it headlessly or via its built-in interactive GUI IDE, GravLang provides a robust environment to learn parsing, interpreting, and language design.

---

## 📑 Table of Contents

- [✨ Key Features](#-key-features)
- [🚀 Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
- [💻 Usage](#-usage)
  - [Interactive GUI IDE](#interactive-gui-ide)
  - [Headless Execution](#headless-execution)
- [📖 Language Tour](#-language-tour)
  - [Variables & Types](#variables--types)
  - [Control Flow](#control-flow)
  - [Functions & Arrays](#functions--arrays)
  - [Object-Oriented Programming](#object-oriented-programming)
- [🧩 Architecture](#-architecture)
- [📜 License](#-license)

---

## ✨ Key Features

- **Multi-Paradigm:** Supports procedural and object-oriented programming.
- **Dynamic Typing:** Intuitive let-bound variable declarations.
- **Rich Standard Library:** Built-in support for array manipulation (`push`, `len`, `sort`, `contains`) and type-casting (`toInt`, `toFloat`, `toString`).
- **Control Structures:** `if / elif / else` conditions, `while / for / for...in` loops perfectly supported with `break` and `continue`.
- **First-class Functions:** Supports recursion and intuitive parameter passing.
- **Object-Oriented Core:** Natively supports classes, inheritance (`extends`), constructors (`init`), methods, and instance properties (`self`).
- **Comprehensive Test Suite:** Packed with an extensive `sample.grav` script that tests all language features.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher is required.

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/GravLang.git
   cd GravLang
   ```
2. (Optional) Set up a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

---

## 💻 Usage

GravLang comes with a standard CLI entry point (`main.py`) that seamlessly routes between the interactive environment and script execution.

### Interactive GUI IDE

Launch the built-in GravLang IDE for interactive coding, syntax highlighting, and visual execution:

```bash
python main.py
```

### Headless Execution

Execute a `.grav` source file directly from your terminal. Ideal for automation and CI environments:

```bash
python main.py sample.grav
```

---

## 📖 Language Tour

Here is a quick overview of GravLang's expressive syntax.

### Variables & Types

GravLang uses `let` for variable declarations and supports native integers, floats, strings, booleans, and null types.

```javascript
let title = "GravLang";
let pi = 3.14159;
let isActive = true;
let emptyState = null;

print(title + " version: " + toString(pi));
```

### Control Flow

Standard conditional structures and augmented assignments (`+=`, `-=`, `*=`).

```javascript
let score = 85;

if (score >= 90) {
    print("Grade: A");
} elif (score >= 80) {
    print("Grade: B");
} else {
    print("Needs Improvement");
}
```

### Functions & Arrays

Functions are highly capable and support recursive calls. Arrays support powerful built-in mutation.

```javascript
# Factorial Function
func factorial(n) {
    if (n <= 1) { return 1; }
    return n * factorial(n - 1);
}
print(factorial(5)); # 120

# Array Iteration
let colors = ["red", "green", "blue"];
push(colors, "yellow");

for (color in colors) {
    print("Color found: " + color);
}
```

### Object-Oriented Programming

Create elegant architectures using classes, instances, and inheritance.

```javascript
class Animal {
    func init(name, sound) {
        self.name = name;
        self.sound = sound;
    }
    func speak() {
        print(self.name + " says: " + self.sound);
    }
}

class Dog extends Animal {
    func init(name) {
        self.name = name;
        self.sound = "Woof!";
        self.tricks = [];
    }
    func learnTrick(trick) {
        push(self.tricks, trick);
    }
}

let dog = Dog("Buddy");
dog.speak();          # Buddy says: Woof!
dog.learnTrick("Sit");
```

---

## 🧩 Architecture

GravLang is cleanly separated into modular components commonly found in compiler design:

- **Lexer (`lexer.py`):** Tokenizes incoming raw source code into structured tokens.
- **Parser (`parser.py`):** Converts the token stream into an Abstract Syntax Tree (AST) defined in `ast_nodes.py`.
- **Interpreter (`interpreter.py`):** Traverses the AST and executes the program logic against the defined `environment.py`.
- **Built-ins (`builtins.py`):** Provides native functions (`print`, `len`, `push`, type casting) that interface directly with the Python backend.

---

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.
