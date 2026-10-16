use std::{fs,path::PathBuf,process::Command};
use kache_store::link::prepare_writable_target_from_file;
fn main() {
    let root=PathBuf::from(std::env::args_os().nth(1).unwrap());
    fs::create_dir_all(&root).unwrap();
    let source=root.join("source.o");
    let restored=root.join("restored.o");
    let compiler=root.join("compiler.o");
    fs::write(&source,b"cached object").unwrap();
    assert!(Command::new("/bin/chmod").args(["+a","user:nobody allow read"]).arg(&source).status().unwrap().success());
    fs::write(&compiler,b"fresh object").unwrap();
    prepare_writable_target_from_file(&source,&restored).unwrap().publish().unwrap();
    let listing=Command::new("/bin/ls").args(["-le"]).args([&source,&compiler,&restored]).output().unwrap();
    println!("{}",String::from_utf8_lossy(&listing.stdout));
    let target=Command::new("/bin/ls").args(["-le"]).arg(&restored).output().unwrap();
    assert!(!String::from_utf8_lossy(&target.stdout).contains("user:nobody"),"restored compiler output retained source ACL instead of target creation ACL");
}
