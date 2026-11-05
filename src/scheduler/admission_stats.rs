//! What a thread's admissions cost: tries, waits and holds of `queue.lock`,
//! and parks. Counted per thread: a wrapper admits on the thread that runs
//! it, and a test binary runs many admissions in one process.

use serde::Serialize;
use std::cell::Cell;
use std::time::Duration;

/// The thread's counts since its last [`take`].
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub struct AdmissionStats {
    /// Passes through admission: a plan under `queue.lock` or out of order.
    pub admit_calls: u32,
    /// Non-blocking tries of `queue.lock`.
    pub lock_attempts: u64,
    /// Time spent trying `queue.lock`, taken or not.
    pub lock_wait_us: u64,
    /// Times `queue.lock` was taken.
    pub lock_holds: u32,
    /// Time `queue.lock` was held.
    pub lock_hold_us: u64,
    /// Times the wait for `queue.lock` ran out.
    pub lock_gave_up: u32,
    /// Sleeps until a slot release or the end of a slice.
    pub parks: u32,
    /// Time asleep in those parks.
    pub park_us: u64,
    /// Admissions that took slots out of order, without `queue.lock`.
    pub unordered: u32,
    /// Admissions that took the slots a releaser's plan assigned, without
    /// planning again.
    pub claims: u32,
}

impl AdmissionStats {
    pub const ZERO: Self = Self {
        admit_calls: 0,
        lock_attempts: 0,
        lock_wait_us: 0,
        lock_holds: 0,
        lock_hold_us: 0,
        lock_gave_up: 0,
        parks: 0,
        park_us: 0,
        unordered: 0,
        claims: 0,
    };
}

thread_local! {
    static STATS: Cell<AdmissionStats> = const { Cell::new(AdmissionStats::ZERO) };
}

fn update(change: impl FnOnce(&mut AdmissionStats)) {
    STATS.with(|stats| {
        let mut current = stats.get();
        change(&mut current);
        stats.set(current);
    });
}

pub(super) fn admit_called() {
    update(|stats| stats.admit_calls = stats.admit_calls.saturating_add(1));
}

pub(super) fn lock_attempted() {
    update(|stats| stats.lock_attempts = stats.lock_attempts.saturating_add(1));
}

/// A try for `queue.lock` ended after `spent`; `gave_up` when it ran out.
pub(super) fn lock_waited(spent: Duration, gave_up: bool) {
    update(|stats| {
        stats.lock_wait_us = stats.lock_wait_us.saturating_add(micros(spent));
        if gave_up {
            stats.lock_gave_up = stats.lock_gave_up.saturating_add(1);
        }
    });
}

pub(super) fn lock_held(spent: Duration) {
    update(|stats| {
        stats.lock_holds = stats.lock_holds.saturating_add(1);
        stats.lock_hold_us = stats.lock_hold_us.saturating_add(micros(spent));
    });
}

pub(super) fn parked(spent: Duration) {
    update(|stats| {
        stats.parks = stats.parks.saturating_add(1);
        stats.park_us = stats.park_us.saturating_add(micros(spent));
    });
}

pub(super) fn admitted_unordered() {
    update(|stats| stats.unordered = stats.unordered.saturating_add(1));
}

pub(super) fn claimed() {
    update(|stats| stats.claims = stats.claims.saturating_add(1));
}

/// The thread's counts, which start again from zero.
pub fn take() -> AdmissionStats {
    STATS.with(|stats| stats.replace(AdmissionStats::ZERO))
}

/// Whole microseconds, saturating at `u64::MAX`.
pub(crate) fn micros(duration: Duration) -> u64 {
    duration.as_micros().try_into().unwrap_or(u64::MAX)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn take_returns_every_count_and_starts_again() {
        let _ = take();
        admit_called();
        lock_attempted();
        lock_attempted();
        lock_waited(Duration::from_micros(7), true);
        lock_held(Duration::from_micros(5));
        parked(Duration::from_micros(3));
        admitted_unordered();
        claimed();
        assert_eq!(
            take(),
            AdmissionStats {
                admit_calls: 1,
                lock_attempts: 2,
                lock_wait_us: 7,
                lock_holds: 1,
                lock_hold_us: 5,
                lock_gave_up: 1,
                parks: 1,
                park_us: 3,
                unordered: 1,
                claims: 1,
            }
        );
        assert_eq!(take(), AdmissionStats::ZERO);
    }

    #[test]
    fn a_lock_taken_in_time_counts_its_wait_but_no_give_up() {
        let _ = take();
        lock_waited(Duration::from_micros(4), false);
        let stats = take();
        assert_eq!((stats.lock_wait_us, stats.lock_gave_up), (4, 0));
    }

    #[test]
    fn counts_are_per_thread() {
        let _ = take();
        admit_called();
        let other = std::thread::spawn(take).join().unwrap();
        assert_eq!(other, AdmissionStats::ZERO);
        assert_eq!(take().admit_calls, 1);
    }
}
