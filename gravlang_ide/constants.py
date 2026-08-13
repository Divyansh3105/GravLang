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
KEYWORDS   = r'\b(let|if|else|while|for|in|func|return|class|extends|import|new|null|and|or|not)\b'
BUILTINS   = r'\b(print|len|type|push|pop|sort|toString|range|input|parseInt|parseFloat|append|insert|remove|keys|values|hasKey)\b'
STRINGS    = r'"(?:[^"\\]|\\.)*"'
NUMBERS    = r'\b\d+(?:\.\d+)?\b'
COMMENTS   = r'#.*'
BOOLEANS   = r'\b(true|false)\b'
SELF_KW    = r'\bself\b'
CLASS_NAME = r'(?<=class\s)\w+'
AUG_OPS    = r'(//=|%=|\+=|-=|\*=|/=)'  # FIXED: added //= and %= for syntax highlighting

_AC_KEYWORDS = [
    "let", "if", "elif", "else", "while", "for", "in", "func", "return",
    "class", "extends", "true", "false", "null", "self",
    "and", "or", "not", "break", "continue", "try", "catch", "throw",
    "import", "finally", "new",
]
_AC_BUILTINS = [
    "print", "len", "type", "push", "pop", "sort", "toString",
    "input", "toInt", "toFloat", "hasAttr",
    "keys", "values", "has", "del",
    "remove", "contains", "reverse",
]

# Category icons shown as a prefix in the listbox
_CAT_ICON = {"keyword": "⚡", "builtin": "◆", "user": "○"}
