# Data Structures

GravLang provides robust composite data structures natively: Arrays and Dictionaries.

## Arrays

Arrays are ordered sequences of values. They are mutable, 0-indexed, and can contain mixed types.

```js
let arr = [1, "two", 3.0, [4]];
```

### Access and Assignment

```js
let first = arr[0];
arr[1] = 2;
```

### Slicing

GravLang supports array slicing `arr[start:stop]`:

```js
let nums = [10, 20, 30, 40, 50];
let slice1 = nums[1:3]; # [20, 30]
let slice2 = nums[:2];  # [10, 20]
let slice3 = nums[3:];  # [40, 50]
```

### Array Built-ins

GravLang provides multiple built-in functions for array manipulation:

- `push(arr, value)`: Appends value to the end and returns the mutated array.
- `pop(arr)`: Removes and returns the last element.
- `remove(arr, index)`: Removes and returns the element at the specified index.
- `contains(arr, value)`: Returns `true` if the array contains the value.
- `reverse(arr)`: Reverses the array in place.
- `sort(arr)`: Sorts the array in place (elements must be comparable).

```js
let letters = ["a", "b", "c"];
push(letters, "d");
pop(letters);
```

## Dictionaries

Dictionaries (dicts) store key-value pairs. Keys can be strings, integers, or floats.

```js
let dict = {
    "name": "GravLang",
    "version": 1.0,
    1: "one"
};
```

### Access and Assignment

```js
print(dict["name"]); # GravLang
dict["author"] = "Open Source";
```

### Dict Built-ins

GravLang provides built-in functions for dictionaries:

- `keys(dict)`: Returns an array of all keys.
- `values(dict)`: Returns an array of all values.
- `has(dict, key)`: Returns `true` if the key exists in the dictionary.
- `del(dict, key)`: Deletes the key from the dictionary. Raises an error if the key is missing.

```js
let k = keys(dict);
if (has(dict, "version")) {
    del(dict, "version");
}
```

### Length
You can get the number of items in both arrays and dictionaries using `len()`:

```js
len([1, 2, 3]);       # 3
len({ "a": 1 });      # 1
len("hello world");   # 11
```
