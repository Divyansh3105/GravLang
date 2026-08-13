# Control Flow & Error Handling

## If / Elif / Else Statements

GravLang uses standard `if`, `elif`, and `else` constructs. Parentheses around conditions are optional but idiomatic.

```js
let score = 85;

if (score >= 90) {
    print("Grade: A");
} elif (score >= 80) {
    print("Grade: B");
} else {
    print("Grade: C");
}
```

**Note:** The logical operators are `and`, `or`, and `not`.

```js
if (score > 50 and not is_absent) { ... }
```

## Loops

GravLang provides robust loop constructs, including advanced `else` and `finally` blocks for loops.

### While Loop

Standard while loop with optional `else` and `finally` blocks.

```js
let i = 0;
while (i < 5) {
    print(i);
    i += 1;
}
```

### For Loop

Standard C-style `for` loop with `init; condition; update`:

```js
for (let i = 0; i < 5; i += 1) {
    print(i);
}
```

### For-In Loop

Iterate over an array (iterable):

```js
let arr = [10, 20, 30];
for (item in arr) {
    print(item);
}
```

### Loop `else` and `finally`

GravLang loops can optionally include `else` and `finally` blocks:
- **`else`**: Runs ONLY if the loop finishes naturally (i.e., condition becomes false or iteration ends) and was NOT terminated by a `break`.
- **`finally`**: Runs unconditionally after the loop, regardless of how it ended.

```js
for (item in [1, 2, 3]) {
    if (item == 5) {
        print("Found 5!");
        break;
    }
} else {
    print("5 was never found.");
} finally {
    print("Loop execution completed.");
}
```

## Error Handling

GravLang supports robust error handling using `try`, `catch`, and `finally`, as well as raising errors using `throw`.

```js
try {
    let result = 10 / 0;
} catch (err) {
    print("Caught an error:");
    print(err);
} finally {
    print("Always runs.");
}
```

### Throwing Errors

You can raise exceptions using the `throw` keyword:

```js
if (score < 0) {
    throw "Score cannot be negative!";
}
```
