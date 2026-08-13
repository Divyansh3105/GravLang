# Classes & Object-Oriented Programming

GravLang supports object-oriented programming via classes and single inheritance.

## Defining a Class

Classes are defined using the `class` keyword. 

To initialize instances, you can define an `init` method. Instance methods are defined inside the class block using `func`.

```js
class Animal {
    func init(name) {
        self.name = name;
    }

    func speak() {
        print(f"{self.name} makes a noise.");
    }
}
```

## Instantiation

To instantiate a class, call it like a function:

```js
let pet = Animal("Dog");
pet.speak(); # Dog makes a noise.
```

## The `self` Keyword

The `self` keyword refers to the current instance of the class. It is required to access or modify instance properties from within a class method.

```js
class Counter {
    func init() {
        self.count = 0;
    }

    func increment() {
        self.count += 1;
        return self.count;
    }
}
```

## Inheritance

GravLang supports single inheritance using the `extends` keyword. A subclass inherits all methods from its parent class.

```js
class Dog extends Animal {
    func speak() {
        print(f"{self.name} barks!");
    }
}

let fido = Dog("Fido");
fido.speak(); # Fido barks!
```

**Note:** If you override `init`, the parent class's `init` is not implicitly called. You can, however, manually invoke methods if required.

## Introspection

You can check an object's type and its properties using built-in functions:

```js
let obj = Animal("Cat");

print(type(obj)); # "Animal"
print(hasAttr(obj, "name")); # true
```
