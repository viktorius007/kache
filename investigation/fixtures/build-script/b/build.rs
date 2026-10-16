fn main(){
println!("cargo:rerun-if-changed=input.txt");
println!("cargo:rerun-if-env-changed=AUDIT_SCRIPT_VALUE");
let out=std::path::PathBuf::from(std::env::var("OUT_DIR").unwrap());
let input=std::fs::read_to_string("input.txt").unwrap();
let value=std::env::var("AUDIT_SCRIPT_VALUE").unwrap_or_else(|_| "unset".into());
std::fs::write(out.join("generated.txt"),format!("{}:{}",input,value)).unwrap();
}
