import re

SAMPLES = {
    "Hello World": '# Hello World\nprint("Hello, World!");\n',

    "Fibonacci": '''\
# Fibonacci sequence
func fib(n) {
    if (n <= 1) { return n; }
    return fib(n - 1) + fib(n - 2);
}

let i = 0;
while (i < 10) {
    print(fib(i));
    i = i + 1;
}
''',
    "FizzBuzz": '''\
# FizzBuzz
let i = 1;
while (i <= 20) {
    if (i % 15 == 0) { print("FizzBuzz"); }
    elif (i % 3 == 0) { print("Fizz"); }
    elif (i % 5 == 0) { print("Buzz"); }
    else { print(i); }
    i = i + 1;
}
''',
    "Bubble Sort": '''\
# Bubble Sort
func bubbleSort(arr) {
    let n = len(arr);
    let i = 0;
    while (i < n) {
        let j = 0;
        while (j < n - i - 1) {
            if (arr[j] > arr[j + 1]) {
                let tmp = arr[j];
                arr[j] = arr[j + 1];
                arr[j + 1] = tmp;
            }
            j += 1;
        }
        i += 1;
    }
    return arr;
}

let nums = [64, 34, 25, 12, 22, 11, 90];
bubbleSort(nums);
print(toString(nums));
''',
    "Stack Class": '''\
# Stack Class
class Stack {
    func init() {
        self.items = [];
    }
    func push(item) {
        push(self.items, item);
    }
    func pop() {
        return pop(self.items);
    }
    func peek() {
        return self.items[len(self.items) - 1];
    }
    func isEmpty() {
        return len(self.items) == 0;
    }
    func size() {
        return len(self.items);
    }
}

let s = Stack();
s.push(1);
s.push(2);
s.push(3);
print(s.peek());
print(s.pop());
print(s.size());
''',
    "Calculator Class": '''\
# Simple Calculator
class Calculator {
    func init() {
        self.result = 0;
    }
    func add(n) { self.result = self.result + n; return self; }
    func sub(n) { self.result = self.result - n; return self; }
    func mul(n) { self.result = self.result * n; return self; }
    func reset() { self.result = 0; return self; }
    func display() { print(self.result); }
}

let calc = Calculator();
calc.add(10).mul(3).sub(5).display();
''',
    "For-In Loop Demo": '''\
# For-In Loop demo
let fruits = ["apple", "banana", "cherry", "date"];
for (f in fruits) {
    print("Fruit: " + f);
}

let nums = [5, 3, 8, 1, 9, 2];
sort(nums);
print(toString(nums));
''',
    "Animals (Final Test)": '''\
class Animal {
    func init(name, sound) {
        self.name = name;
        self.sound = sound;
    }
    func speak() {
        print(self.name + " says " + self.sound);
    }
}

let animals = [
    Animal("Cat", "meow"),
    Animal("Dog", "woof"),
    Animal("Cow", "moo"),
];

for (a in animals) {
    a.speak();
}

let nums = [5, 3, 8, 1, 9, 2];
sort(nums);
print(toString(nums));
''',
}

# ─────────────────────────────────────────────────────────────────────────────
#  KEYWORDS for syntax highlighting
# ─────────────────────────────────────────────────────────────────────────────
from ..core.lexer import KEYWORDS as _LEX_KEYWORDS
from ..core.grav_builtins import BUILTINS as _CORE_BUILTINS

_LITERAL_WORDS = {"true", "false", "self", "print"}   # coloured by their own rules
_KEYWORD_LIST = sorted(w for w in _LEX_KEYWORDS if w not in _LITERAL_WORDS)
_BUILTIN_LIST = sorted(_CORE_BUILTINS)

KEYWORD_SET = frozenset(_KEYWORD_LIST)
BUILTIN_SET = frozenset(_BUILTIN_LIST)
BOOLEAN_SET = frozenset({"true", "false"})

# One scanner for the whole file: comments and strings are matched first, so a
# '#' inside a string (or a keyword inside a comment) is never mis-coloured.
TOKEN_RE = re.compile(
    r'(?P<comment>\#[^\n]*)'
    r'|(?P<string>f?"(?:[^"\\]|\\.)*")'
    r'|(?P<number>\b\d+(?:\.\d+)?\b)'
    r'|(?P<augop>//=|%=|\+=|-=|\*=|/=)'
    r'|(?P<word>[A-Za-z_][A-Za-z0-9_]*)'
)

_AC_KEYWORDS = _KEYWORD_LIST + ["true", "false", "self"]
_AC_BUILTINS = _BUILTIN_LIST

# Category icons shown as a prefix in the listbox
_CAT_ICON = {"keyword": "⚡", "builtin": "◆", "user": "○"}
