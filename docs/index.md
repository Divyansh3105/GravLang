# GravLang

GravLang is a dynamically typed, interpreted programming language with a clean syntax that bridges imperative control flow with functional features (lambdas) and object-oriented paradigms. 

## Features
- **Dynamic Typing:** No need to declare variable types.
- **First-Class Functions:** Anonymous functions (lambdas) can be passed around and returned.
- **Robust Error Handling:** Full `try / catch / finally` support.
- **Advanced Control Flow:** `else` and `finally` blocks for `while` and `for` loops.
- **Object-Oriented Programming:** Classes, methods, and single inheritance.
- **Modular:** Import other `.grav` files easily.

## Quickstart

Save this file as `hello.grav`:

```js
# This is a comment
let message = "Hello, World!";
print(message);

func fib(n) {
    if (n <= 1) { return n; }
    return fib(n - 1) + fib(n - 2);
}

print("Fibonacci of 10 is:");
print(fib(10));
```

Run it via the terminal:
```bash
python main.py hello.grav
```

Or open the interactive GUI debugger:
```bash
python main.py
```
