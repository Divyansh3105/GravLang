func runBrainfuck(source) {
    let tape = [];
    for (let i = 0; i < 30000; i += 1) {
        push(tape, 0);
    }

    let dp = 0;
    let ip = 0;
    let programLength = len(source);

    print("--- Executing Brainfuck ---");

    while (ip < programLength) {
        let cmd = source[ip];

        if (cmd == ">") {
            dp += 1;
            if (dp >= 30000) { dp = 0; }
        } elif (cmd == "<") {
            dp -= 1;
            if (dp < 0) { dp = 29999; }
        } elif (cmd == "+") {
            tape[dp] = (tape[dp] + 1) % 256;
        } elif (cmd == "-") {
            tape[dp] = (tape[dp] - 1) % 256;
            if (tape[dp] < 0) { tape[dp] = 255; }
        } elif (cmd == ".") {
            print("Output (ASCII code): " + toString(tape[dp]));
        } elif (cmd == ",") {
            let val = input("Input a number for cell " + toString(dp) + ": ");
            try {
                tape[dp] = toInt(val) % 256;
            } catch (e) {
                tape[dp] = 0;
            }
        } elif (cmd == "[") {
            if (tape[dp] == 0) {
                # Jump past the matching ]
                let openBrackets = 1;
                while (openBrackets > 0) {
                    ip += 1;
                    if (ip >= programLength) { throw "Unmatched ["; }
                    if (source[ip] == "[") { openBrackets += 1; }
                    elif (source[ip] == "]") { openBrackets -= 1; }
                }
            }
        } elif (cmd == "]") {
            if (tape[dp] != 0) {
                # Jump back to the matching [
                let closeBrackets = 1;
                while (closeBrackets > 0) {
                    ip -= 1;
                    if (ip < 0) { throw "Unmatched ]"; }
                    if (source[ip] == "]") { closeBrackets += 1; }
                    elif (source[ip] == "[") { closeBrackets -= 1; }
                }
            }
        }

        ip += 1;
    }

    print("\n--- Execution Complete ---");
}

let hello_world = [
    "+", "+", "+", "+", "+", "+", "+", "+", "[", ">", "+", "+", "+", "+",
    "[", ">", "+", "+", ">", "+", "+", "+", ">", "+", "+", "+", ">", "+",
    "<", "<", "<", "<", "-", "]", ">", "+", ">", "+", ">", "-", ">", ">",
    "+", "[", "<", "]", "<", "-", "]", ">", ">", ".", ">", "-", "-", "-",
    ".", "+", "+", "+", "+", "+", "+", "+", ".", ".", "+", "+", "+", ".",
    ">", ">", ".", "<", "-", ".", "<", ".", "+", "+", "+", ".", "-", "-",
    "-", "-", "-", "-", ".", "-", "-", "-", "-", "-", "-", ".", ">", "+",
    ".", ">", "."
];

print("Running Hello World in Brainfuck...");
runBrainfuck(hello_world);
