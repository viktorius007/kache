//! Keep Linux children from inheriting writable executable descriptors.
//!
//! Close-on-exec is too late: a forked child retains a descriptor until exec,
//! so Linux can refuse execution of the file after its writer has closed it.
//! Materializations may overlap each other, but cannot overlap process creation.

#[cfg(target_os = "linux")]
use std::sync::{RwLock, RwLockReadGuard, RwLockWriteGuard};

#[cfg(target_os = "linux")]
static ADMISSION: RwLock<()> = RwLock::new(());

/// Hold for the lifetime of writable executable descriptors, never around
/// postprocessing that might itself start a child.
#[cfg(target_os = "linux")]
pub fn materialize() -> RwLockReadGuard<'static, ()> {
    ADMISSION
        .read()
        .unwrap_or_else(|poison| poison.into_inner())
}

/// Hold through process creation only, never through its wait.
#[cfg(target_os = "linux")]
pub fn spawn() -> RwLockWriteGuard<'static, ()> {
    ADMISSION
        .write()
        .unwrap_or_else(|poison| poison.into_inner())
}

/// Test the actual admission state without waiting or using a clock.
#[cfg(all(target_os = "linux", feature = "testing"))]
pub fn materialization_is_excluded() -> bool {
    matches!(
        ADMISSION.try_read(),
        Err(std::sync::TryLockError::WouldBlock)
    )
}

/// Test the actual admission state without waiting or using a clock.
#[cfg(all(target_os = "linux", feature = "testing"))]
pub fn spawn_is_excluded() -> bool {
    matches!(
        ADMISSION.try_write(),
        Err(std::sync::TryLockError::WouldBlock)
    )
}
