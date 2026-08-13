# Variables & Data Types

GravLang is a dynamically typed language, which means you do not declare types for variables. Type checking happens at runtime.

## Variables

Variables are declared using the `let` keyword. Once declared, you can assign them new values without `let`.

```js
let x = 10;
x = "Now I am a string!";

let y = 3.14;
```

Variables can also be modified using augmented assignment operators: `+=`, `-=`, `*=`, `/=`, `//=`, `%=`.

```js
let count = 0;
count += 1;
count *= 10;
```

## Data Types

GravLang supports several primitive and composite data types natively.

### 1. Integers
Whole numbers.

```js
let age = 30;
```

### 2. Floats
Decimal numbers.

```js
let pi = 3.14159;
```

### 3. Strings
Strings can be defined using double quotes `""`. GravLang also supports f-strings for string interpolation using `f"..."`.

```js
let name = "Alice";
let greeting = f"Hello, {name}!";
```

### 4. Booleans
`true` or `false` (case-sensitive).

```js
let is_valid = true;
let is_finished = false;
```

### 5. Null
Represents the intentional absence of any value. The keyword is `null` (not `None` or `nil`).

```js
let empty = null;
```

### 6. Arrays (Lists)
Ordered sequences of items, separated by commas, enclosed in square brackets `[]`. Arrays are mutable.

```js
let nums = [1, 2, 3];
```

### 7. Dictionaries (Dicts)
Key-value pairs enclosed in curly braces `{}`. Keys can be strings, integers, or floats. Values can be of any type.

```js
let person = { "name": "Bob", "age": 25 };
```

## Type Conversion
GravLang provides built-in functions to safely convert between data types:
- `toInt(value)`
- `toFloat(value)`
- `toString(value)`

```js
let n = toInt("42");
let text = toString(100);
```
