fn main() {
    let path = std::env::args_os().nth(1).expect("path");
    let bytes = std::fs::read(path).expect("read");
    println!("{}", blake3::hash(&bytes).to_hex());
}
