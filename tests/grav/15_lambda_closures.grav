let x = 10;

let add_x = func(n) { return n + x; };
print(add_x(5));

func make_counter() {
    let count = 0;
    return func() {
        count += 1;
        return count;
    };
}

let counter = make_counter();
print(counter());
print(counter());
print(counter());
