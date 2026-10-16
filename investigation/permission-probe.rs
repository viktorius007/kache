use std::{fs,path::PathBuf};
use std::os::unix::fs::{MetadataExt,PermissionsExt};
use kache_store::{ArtifactStore,ArtifactPolicy,config::Config,link::*};
struct Policy;
impl ArtifactPolicy for Policy {
 fn allow_hardlink(_: &str)->bool { true }
 fn allow_empty(_: &str,_:&[String])->bool { false }
 fn emit_kind(_: &str)->Option<&'static str>{Some("link")}
 fn stable_after_store(_: &str)->bool {true}
}
fn main(){
 let root=PathBuf::from(std::env::args_os().nth(1).unwrap());

 let restore_dir=root.join("restore-controls");fs::create_dir_all(&restore_dir).unwrap();
 for mode in [0o444,0o555] {
  for (i,strategy) in [LinkStrategy::Hardlink,LinkStrategy::Copy,LinkStrategy::ExecutableHardlink].into_iter().enumerate(){
   let blob=restore_dir.join(format!("blob-{mode:o}-{i}"));let out=restore_dir.join(format!("out-{mode:o}-{i}"));
   let bytes=b"generated fixture artifact";fs::write(&blob,bytes).unwrap();fs::set_permissions(&blob,fs::Permissions::from_mode(mode)).unwrap();
   link_to_target(&blob,&out,strategy).unwrap();let bm=fs::metadata(&blob).unwrap();let om=fs::metadata(&out).unwrap();
   println!("RESTORE {strategy:?} source_mode={mode:o} output_mode={:o} shared={}",om.mode()&0o777,bm.ino()==om.ino());
   assert_eq!(fs::read(&out).unwrap(),bytes);assert_eq!(bm.mode()&0o222,0,"restore made published source writable");
   let result=fs::write(&out,b"consumer rewrite");
   if bm.ino()==om.ino(){assert!(result.is_err(),"shared restored output allowed content mutation");}else{result.unwrap();}
   assert_eq!(fs::read(&blob).unwrap(),bytes,"consumer rewrite corrupted published source");
  }
 }
 let blob=restore_dir.join("writable-blob");fs::write(&blob,b"private cc output").unwrap();fs::set_permissions(&blob,fs::Permissions::from_mode(0o444)).unwrap();
 let out=restore_dir.join("private-target.o");prepare_writable_target_from_file(&blob,&out).unwrap().publish().unwrap();
 assert_ne!(fs::metadata(&out).unwrap().ino(),fs::metadata(&blob).unwrap().ino());fs::write(&out,b"rewritten cc output").unwrap();assert_eq!(fs::read(&blob).unwrap(),b"private cc output");
 let out=restore_dir.join("transformed.d");write_restored(&out,b"expanded depinfo",LinkStrategy::Hardlink).unwrap();fs::write(&out,b"new depinfo").unwrap();
 println!("RESTORE_CONTROLS_GREEN");
 let independent=std::env::args().nth(2).as_deref()==Some("independent");
 let cache=root.join(if independent {"independent-api-cache"} else {"api-cache"}); let cfg=Config{cache_dir:cache,max_size:1<<28,gc_evict_shared:false,upload_spool_max_jobs:8,deferred_durability:false};
 let store=ArtifactStore::<Policy>::open(cfg).unwrap();
 let src=root.join("source.rlib"); fs::write(&src,b"generated artifact 73").unwrap();
 let files=vec![(src.clone(),"libfixture.rlib".to_string())];
 let put=|key:&str,files:&[(PathBuf,String)]|(if independent {store.put_with_compile_time_independent(key,"fixture",&["rlib".into()],&[],"fixture","debug",files,"","",1)} else {store.put_with_compile_time(key,"fixture",&["rlib".into()],&[],"fixture","debug",files,"","",1)}).unwrap();
 put(&"a".repeat(64),&files); let blob=store.blob_path(&kache_store::file_hash::hash_file(&src).unwrap());
 let m=fs::metadata(&blob).unwrap();println!("PUBLISHED mode={:o} inode={} source_inode={} nlink={}",m.mode()&0o777,m.ino(),fs::metadata(&src).unwrap().ino(),m.nlink());
 assert_eq!(m.mode()&0o222,0,"new blob must be read-only");
 // Duplicate source is already a hardlink to this published blob.
 put(&"b".repeat(64),&files);
 let m=fs::metadata(&blob).unwrap();println!("AFTER_DUPLICATE mode={:o} inode={} nlink={}",m.mode()&0o777,m.ino(),m.nlink());
 let before=fs::read(&blob).unwrap();let write=fs::write(&src,b"corrupted through source hardlink");
 println!("SOURCE_WRITE {:?}; BLOB_CHANGED {}",write,fs::read(&blob).unwrap()!=before);
 if independent {assert_eq!(fs::read(&blob).unwrap(),before,"independent source mutation changed blob");println!("INDEPENDENT_BLOB_PROTECTED");}
 assert_eq!(m.mode()&0o222,0,"PUBLISHED_BLOB_BECAME_WRITABLE: duplicate publication cleared read-only on existing shared blob");
}
