macro_rules! include { ($path:expr) => { $path }; }
pub const BAKED: &str = include!(env!("OUT_DIR"));
pub const TEXT: &str = include_str!(concat!(env!("OUT_DIR"), "/data.txt"));
