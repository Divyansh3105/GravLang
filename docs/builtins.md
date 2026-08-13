# Built-in Functions

GravLang comes with a standard library of built-in functions available in the global scope.

## I/O

- **`print(*args)`**
  Outputs arguments to the console.

- **`input(prompt="")`**
  Prompts the user for input and reads a line from stdin as a string.

## Introspection

- **`len(value)`**
  Returns the length of a string, array, or dict. Raises an error for other types.

- **`type(value)`**
  Returns a string representing the type of the value (e.g., `"null"`, `"bool"`, `"int"`, `"float"`, `"string"`, `"array"`, `"dict"`, or the class name of an object).

- **`hasAttr(obj, name)`**
  Returns `true` if the given instance object has an attribute matching the `name` string.

## Type Conversion

- **`toInt(value)`**
  Converts the value to an integer. Raises an error if conversion fails.

- **`toFloat(value)`**
  Converts the value to a float. Raises an error if conversion fails.

- **`toString(value)`**
  Converts the value to its string representation (including robust serialization for arrays and dicts).

## Array Operations

- **`push(arr, value)`**
  Appends `value` to the end of `arr`. Returns the mutated array.

- **`pop(arr)`**
  Removes and returns the last element of the array.

- **`remove(arr, index)`**
  Removes and returns the element at the specified `index`.

- **`contains(arr, value)`**
  Returns `true` if `value` exists inside `arr`.

- **`reverse(arr)`**
  Reverses `arr` in place and returns it.

- **`sort(arr)`**
  Sorts `arr` in place. Elements must be comparable.

## Dictionary Operations

- **`keys(dict)`**
  Returns an array of all keys in `dict`.

- **`values(dict)`**
  Returns an array of all values in `dict`.

- **`has(dict, key)`**
  Returns `true` if `key` exists in `dict`.

- **`del(dict, key)`**
  Deletes the `key` from `dict`. Raises an error if the key does not exist.
