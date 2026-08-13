let result = "";
try {
    let x = 1;
    result = "ok";
} catch (e) {
    result = "error";
} finally {
    print("finally ran");
}
print(result);

try {
    throw 42;
} catch (e) {
    print("caught: " + toString(e));
} finally {
    print("done");
}
