# Functions

Functions in GravLang are first-class citizens. They can be stored in variables, passed to other functions, and returned from functions.

## Function Declarations

Functions are defined using the `func` keyword. Parentheses are required. 

```js
func add(a, b) {
    return a + b;
}

print(add(2, 3)); # Output: 5
```

If a function does not explicitly use `return`, it implicitly returns `null`.

## Anonymous Functions (Lambdas)

You can define inline anonymous functions, which evaluate to function objects.

```js
let multiply = func(a, b) {
    return a * b;
};

print(multiply(4, 5)); # Output: 20
```

Because functions are first-class citizens, you can pass them as arguments (higher-order functions):

```js
func operate(a, b, op) {
    return op(a, b);
}

let result = operate(10, 5, func(x, y) {
    return x - y;
});
print(result); # Output: 5
```

## Variadic Arguments (Spread Operator)

GravLang supports variadic arguments via the `...rest` spread operator in the parameter list. It bundles all remaining arguments into an array.

```js
func printAll(first, ...rest) {
    print("First argument:", first);
    print("Remaining arguments:", rest);
}

printAll(1, 2, 3, 4);
# First argument: 1
# Remaining arguments: [2, 3, 4]
```

## Scope and Closures

Functions in GravLang create a new local environment. They can capture variables from their surrounding scope (closures).

```js
func makeCounter() {
    let count = 0;
    return func() {
        count += 1;
        return count;
    };
}

let counter = makeCounter();
print(counter()); # 1
print(counter()); # 2
```
