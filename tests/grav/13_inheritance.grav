class Animal {
    func init(name, sound) {
        self.name = name;
        self.sound = sound;
    }
    func speak() {
        print(self.name + " says: " + self.sound);
    }
    func describe() {
        print("I am an animal named " + self.name);
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
    func showTricks() {
        print(toString(self.tricks));
    }
}

let d = Dog("Buddy");
d.speak();
d.describe();
d.learnTrick("Sit");
d.learnTrick("Roll");
d.showTricks();
