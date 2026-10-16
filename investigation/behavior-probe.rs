use std::{fs,path::{Path,PathBuf}};
use std::os::unix::fs::{MetadataExt,PermissionsExt,symlink};
use kache_store::link::*;
fn main() {
 let root=PathBuf::from(std::env::args_os().nth(1).unwrap());fs::create_dir_all(&root).unwrap();
 let blob=root.join("blob"); fs::write(&blob,b"cached artifact").unwrap();fs::set_permissions(&blob,fs::Permissions::from_mode(0o444)).unwrap();
 for (i,strategy) in [LinkStrategy::Hardlink,LinkStrategy::Copy,LinkStrategy::ExecutableHardlink].into_iter().enumerate(){
  let out=root.join(format!("tree/{i}"));link_to_target(&blob,&out,strategy).unwrap();assert_eq!(fs::read(&out).unwrap(),b"cached artifact");
  let meta=fs::metadata(&out).unwrap();assert_ne!(meta.ino(),fs::metadata(&blob).unwrap().ino(),"APFS clone must be private");
  fs::write(&out,b"rewritten").unwrap();assert_eq!(fs::read(&blob).unwrap(),b"cached artifact");
  println!("APFS strategy {strategy:?}: private and source unchanged");
 }
 let winner=root.join("winner.o");let prepared=prepare_writable_target_from_file(&blob,&winner).unwrap();fs::write(&winner,b"race winner").unwrap();assert!(prepared.publish().is_err());assert_eq!(fs::read(&winner).unwrap(),b"race winner");println!("create-only publication preserved winner");
 let old_alias=root.join("old-alias.o");fs::hard_link(&winner,&old_alias).unwrap();prepare_writable_target_from_bytes(&winner,b"replacement").unwrap().publish_replacing().unwrap();assert_eq!(fs::read(&old_alias).unwrap(),b"race winner");assert_eq!(fs::read(&winner).unwrap(),b"replacement");println!("replacement isolated old hardlink alias");
 let abandoned=root.join("abandoned.o");drop(prepare_writable_target_from_file(&blob,&abandoned).unwrap());assert!(!abandoned.exists());assert!(!fs::read_dir(&root).unwrap().any(|e|e.unwrap().file_name().to_string_lossy().starts_with(".kache-cc-")));println!("abandoned stage cleanup green");
 let link=root.join("symlink");symlink(&blob,&link).unwrap();let mtime=fs::metadata(&blob).unwrap().modified().unwrap();assert!(touch_mtime_write_clock(&link).is_err());assert_eq!(fs::metadata(&blob).unwrap().modified().unwrap(),mtime);println!("symlink stamp refused without source mutation");
 let text="/a/target/demo.d: /a/src/lib.rs /a/target/generated.rs ../relative.h\n# env-dep:OUT_DIR=/a/target/out\n";
 let stored=rewrite_rustc_depinfo_content_with_configured_roots(text,Path::new("/a/target"),Path::new("/a"),Some(Path::new("/a")),&[],DepInfoMode::Relativize);
 let expanded=rewrite_rustc_depinfo_content_with_configured_roots(&stored,Path::new("/b/target"),Path::new("/b"),Some(Path::new("/b")),&[],DepInfoMode::Expand);
 assert_eq!(expanded,text.replace("/a/","/b/"));println!("ordinary source/target/env/relative depinfo relocation green");
}
