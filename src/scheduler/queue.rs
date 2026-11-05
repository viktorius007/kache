//! Order in which waiting requests take permit slots.
//!
//! The slot locks stay the authority for capacity: a request runs only once
//! it holds its slots, and the kernel frees them when its process dies. This
//! module only decides which waiter may take free slots first, so a request
//! that needs many slots is not overtaken forever by smaller ones that arrive
//! after it, and a foreground build does not queue behind background ones.
//!
//! A waiting request keeps a ticket: `queue/<rank>-<kind>-<need>-<id>`, whose
//! content says how often the ticket has been passed and when its owner last
//! looked, and `waiters/<id>`, which the owner holds an exclusive lock on.
//! Every admission decision runs under `queue.lock`, so two waiters never
//! plan with the same free slots. The lock is handed over, not polled: a
//! holder that drops it wakes one process waiting for it through the
//! counter in `queue.wake`.
//!
//! - Rank: the arrival time in milliseconds, less [`FOREGROUND_HEAD_START`]
//!   for a foreground build. Lower ranks go first. A ticket keeps its rank
//!   while later ones arrive, so its priority rises the longer it waits: a
//!   background request that has waited the head start outranks every
//!   foreground request that arrives after.
//! - Free slots go to tickets in rank order, each taking the lowest slots it
//!   can use. A ticket that does not fit is passed by later ones that do.
//! - The first ticket can be passed [`pass_budget`] times. After that it
//!   reserves the free slots it can use, so they add up until it fits. A test
//!   reserves only test slots, and a waiting compile counts them as slots
//!   tests hold (see [`super::compile_need`]): it then fits in the compile
//!   reserve, so a compile a test waits on still runs.
//! - A ticket is live while its owner holds the lock on `waiters/<id>`. A
//!   cancelled waiter removes its ticket; a killed one leaves files whose lock
//!   the kernel has released, and the next planner deletes them. The lock, not
//!   a process ID, says who is alive, so a reused process ID changes nothing.
//! - Whoever frees slots plans for the whole queue ([`wake_admitted`]) and
//!   wakes each ticket the plan admits through the counter in its
//!   `waiters/<id>` file. A parked waiter takes no lock until it is woken or
//!   its backstop runs out (see [`super::Scheduler::park`]).
//! - A ticket that was woken and has not claimed its slots for
//!   [`STALE_AFTER`] is skipped: a waiter the OS has starved of CPU cannot
//!   hold back the queue. It gets its place back the next time it runs.
//!
//! Wrappers of a Kache release from before this queue take free slots
//! without a ticket. Their slots count like any other, but while releases are
//! mixed such a wrapper can take slots a ticket was saving up.

use anyhow::Result;
use std::fs;
use std::io::{Read, Seek, SeekFrom, Write};
use std::path::{Path, PathBuf};
use std::time::{Duration, SystemTime, UNIX_EPOCH};

use super::permit_wait::{WORDS_WAKE, Wake, Word};
use super::priority::Priority;

/// How far ahead of a background request a foreground one arriving at the
/// same time is placed. Well inside the 30 s an ordinary capacity wait may
/// last (see [`super::budget`]), so a background request still in the queue
/// comes to outrank foreground requests that arrive after it.
pub(super) const FOREGROUND_HEAD_START: Duration = Duration::from_secs(10);
/// How long a woken ticket counts before it has claimed its slots.
pub(super) const STALE_AFTER: Duration = Duration::from_secs(2);
/// The longest `queue.lock` goes without changing hands before a waiter
/// stops waiting for it. Planning takes microseconds; only a holder the OS
/// stopped running keeps the lock longer. A lock that keeps changing hands
/// is waited for until the caller's allowance ends.
pub(super) const LOCK_WAIT: Duration = Duration::from_secs(1);
/// The longest a releaser waits for `queue.lock` to plan for the slots it
/// freed. Past this the next holder plans for them.
pub(super) const RELEASE_WAIT: Duration = Duration::from_secs(10);
/// The longest a waiter sleeps for `queue.lock` without trying it where the
/// holder's drop wakes it. A holder that is killed drops the lock without
/// a wake; this bounds what that costs the next waiter.
pub(super) const LOCK_SLICE: Duration = Duration::from_millis(50);
/// The first sleep between tries where nothing wakes a lock waiter. It
/// doubles on every try up to [`LOCK_BACKOFF_MAX`].
pub(super) const LOCK_POLL: Duration = Duration::from_micros(200);
pub(super) const LOCK_BACKOFF_MAX: Duration = Duration::from_millis(5);

pub(super) fn lock_path(root: &Path) -> PathBuf {
    root.join("queue.lock")
}

fn lock_wake_path(root: &Path) -> PathBuf {
    root.join("queue.wake")
}

/// `queue.lock`, held until dropped. Dropping it wakes one process in
/// [`lock`], which is then the first to try the lock.
pub(super) struct QueueLock {
    file: Option<fs::File>,
    word: Word,
}

impl Drop for QueueLock {
    fn drop(&mut self) {
        // Unlock first, so the process that wakes finds the lock free.
        drop(self.file.take());
        self.word.bump_one();
    }
}

/// How long a waiter sleeps before its next try of `queue.lock`: a slice
/// where a drop wakes it (`woken`), a doubling backoff where nothing does.
fn lock_slice(woken: bool, tries: u32, left: Duration) -> Duration {
    let slice = if woken {
        LOCK_SLICE
    } else {
        LOCK_POLL
            .saturating_mul(1 << tries.min(5))
            .min(LOCK_BACKOFF_MAX)
    };
    slice.min(left)
}

/// When `queue.wake` last moved: a holder's drop moves it, so a word that
/// stands still is a holder that keeps the lock.
struct Turnover {
    seen: u32,
    changed: std::time::Instant,
}

impl Turnover {
    fn observe(&mut self, seen: u32, now: std::time::Instant) {
        if seen != self.seen {
            self.seen = seen;
            self.changed = now;
        }
    }

    /// How much of `stale` is left before the lock counts as kept.
    fn left(&self, now: std::time::Instant, stale: Duration) -> Duration {
        stale.saturating_sub(now.saturating_duration_since(self.changed))
    }
}

/// Hold `queue.lock`, waiting up to `wait` for it, and no longer than
/// `stale` since it last changed hands. `None` when it stayed held. The
/// file is never unlinked, so the lock on the open handle is the lock on
/// the path.
///
/// A waiter sleeps on `queue.wake` until the holder drops the lock, with
/// [`LOCK_SLICE`] as the backstop; where nothing wakes it, it tries again
/// on a doubling backoff. A waiter that leaves without the lock passes the
/// wake it may have taken to the next one without moving the word: only a
/// holder's drop counts as the lock changing hands.
pub(super) fn lock(root: &Path, wait: Duration, stale: Duration) -> Result<Option<QueueLock>> {
    let file = fs::OpenOptions::new()
        .read(true)
        .write(true)
        .create(true)
        .truncate(false)
        .open(lock_path(root))?;
    let word = Word::open(&lock_wake_path(root));
    let start = std::time::Instant::now();
    let mut turnover = Turnover {
        seen: word.seen(),
        changed: start,
    };
    let mut tries = 0;
    loop {
        if let Err(error) = crate::invocation::process::check() {
            word.pass_one();
            return Err(error.into());
        }
        super::admission_stats::lock_attempted();
        let seen = word.seen();
        let now = std::time::Instant::now();
        turnover.observe(seen, now);
        match file.try_lock() {
            Ok(()) => {
                super::admission_stats::lock_waited(start.elapsed(), false);
                return Ok(Some(QueueLock {
                    file: Some(file),
                    word,
                }));
            }
            Err(fs::TryLockError::WouldBlock) => {}
            Err(fs::TryLockError::Error(error)) => {
                word.pass_one();
                return Err(error.into());
            }
        }
        let left = wait
            .saturating_sub(now.saturating_duration_since(start))
            .min(turnover.left(now, stale));
        if left.is_zero() {
            super::admission_stats::lock_waited(start.elapsed(), true);
            word.pass_one();
            return Ok(None);
        }
        word.wait(seen, lock_slice(WORDS_WAKE, tries, left));
        tries = tries.saturating_add(1);
    }
}

pub(super) fn queue_dir(root: &Path) -> PathBuf {
    root.join("queue")
}

pub(super) fn waiters_dir(root: &Path) -> PathBuf {
    root.join("waiters")
}

/// How often the first ticket can be passed before it reserves slots: once
/// per slot of the pool.
pub(super) fn pass_budget(pool: u32) -> u32 {
    pool
}

/// Which slots a request can use.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(super) enum Kind {
    /// Any slot.
    Compile,
    /// Slots above the compile reserve.
    Test,
}

impl Kind {
    fn tag(self) -> &'static str {
        match self {
            Self::Compile => "c",
            Self::Test => "t",
        }
    }

    fn from_tag(tag: &str) -> Option<Self> {
        match tag {
            "c" => Some(Self::Compile),
            "t" => Some(Self::Test),
            _ => None,
        }
    }

    pub(super) fn uses(self, index: u32, reserve: u32) -> bool {
        match self {
            Self::Compile => true,
            Self::Test => index >= reserve,
        }
    }
}

/// A queued request, as its ticket name describes it.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(super) struct Entry {
    pub(super) rank: u64,
    pub(super) kind: Kind,
    pub(super) need: u32,
    pub(super) id: String,
}

impl Entry {
    pub(super) fn new(rank: u64, kind: Kind, need: u32) -> Self {
        Self {
            rank,
            kind,
            need,
            id: new_id(),
        }
    }

    pub(super) fn name(&self) -> String {
        format!(
            "{}-{}-{}-{}",
            self.rank,
            self.kind.tag(),
            self.need,
            self.id
        )
    }

    pub(super) fn parse(name: &str) -> Option<Self> {
        let mut fields = name.splitn(4, '-');
        let rank = fields.next()?.parse().ok()?;
        let kind = Kind::from_tag(fields.next()?)?;
        let need = fields.next()?.parse().ok().filter(|need| *need > 0)?;
        let id = fields.next().filter(|id| valid_id(id))?.to_string();
        Some(Self {
            rank,
            kind,
            need,
            id,
        })
    }
}

fn valid_id(id: &str) -> bool {
    !id.is_empty() && id.bytes().all(|byte| byte.is_ascii_alphanumeric())
}

fn new_id() -> String {
    static NEXT: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(0);
    let mut bytes = [0u8; 8];
    if getrandom::fill(&mut bytes).is_err() {
        // Unique among this process's tickets; a live ticket of another
        // process with the same name makes creation fail and the request
        // takes slots out of order.
        let next = NEXT.fetch_add(1, std::sync::atomic::Ordering::Relaxed);
        return fallback_id(std::process::id(), next);
    }
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}

fn fallback_id(pid: u32, sequence: u64) -> String {
    format!("p{pid:x}n{sequence:016x}")
}

pub(super) fn millis(time: SystemTime) -> u64 {
    time.duration_since(UNIX_EPOCH).map_or(0, |since| {
        u64::try_from(since.as_millis()).unwrap_or(u64::MAX)
    })
}

/// The rank of a request arriving at `now`.
pub(super) fn rank(now: SystemTime, priority: Priority) -> u64 {
    let arrived = millis(now);
    match priority {
        Priority::Foreground => arrived.saturating_sub(FOREGROUND_HEAD_START.as_millis() as u64),
        Priority::Background => arrived,
    }
}

/// What a queued request's owner and planners write in its ticket.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub(super) struct State {
    /// Times a later ticket took slots while this one was first and did not
    /// fit.
    pub(super) passes: u32,
    /// When the owner last looked, in milliseconds since the epoch.
    pub(super) seen: u64,
    /// When a planner first told the owner its slots were free, in
    /// milliseconds since the epoch; zero once the owner has looked since.
    pub(super) woken: u64,
    /// The slots the last plan gave the ticket, one bit per slot index;
    /// zero once the owner has looked since, or for a slot past 127.
    pub(super) slots: u128,
}

/// One bit per slot; zero when a slot has no bit.
pub(super) fn slot_mask(slots: &[u32]) -> u128 {
    slots
        .iter()
        .try_fold(0u128, |mask, &index| {
            (index < 128).then(|| mask | (1u128 << index))
        })
        .unwrap_or(0)
}

/// The slots of a mask, lowest first.
fn mask_slots(mask: u128) -> Vec<u32> {
    (0..128)
        .filter(|index| mask & (1u128 << index) != 0)
        .collect()
}

impl State {
    /// Tickets written before `woken` existed have two fields, before
    /// `slots` three.
    fn parse(text: &str) -> Option<Self> {
        let mut fields = text.split_whitespace();
        let passes = fields.next()?.parse().ok()?;
        let seen = fields.next()?.parse().ok()?;
        let woken = match fields.next() {
            Some(field) => field.parse().ok()?,
            None => 0,
        };
        let slots = match fields.next() {
            Some(field) => u128::from_str_radix(field, 16).ok()?,
            None => 0,
        };
        Some(Self {
            passes,
            seen,
            woken,
            slots,
        })
    }

    /// Whether the ticket counts: its owner was not told of free slots, or
    /// was told less than [`STALE_AFTER`] ago.
    fn fresh(self, now: SystemTime) -> bool {
        self.woken == 0 || millis(now).saturating_sub(self.woken) < STALE_AFTER.as_millis() as u64
    }
}

fn read_state(file: &mut fs::File) -> Option<State> {
    let mut text = String::new();
    file.seek(SeekFrom::Start(0)).ok()?;
    file.read_to_string(&mut text).ok()?;
    State::parse(&text)
}

/// Fixed width, overwritten in place: a truncate before the write makes
/// the close after it start a writeback that the next writer waits for.
fn write_state(file: &mut fs::File, state: State) -> Result<()> {
    file.seek(SeekFrom::Start(0))?;
    write!(
        file,
        "{:>10} {:>20} {:>20} {:032x}",
        state.passes, state.seen, state.woken, state.slots
    )?;
    Ok(())
}

/// Every ticket in the queue, in rank order. Names that are not tickets are
/// ignored.
pub(super) fn list(root: &Path) -> Result<Vec<Entry>> {
    let mut entries = Vec::new();
    let items = match fs::read_dir(queue_dir(root)) {
        Ok(items) => items,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(entries),
        Err(error) => return Err(error.into()),
    };
    for item in items {
        if let Some(entry) = item?.file_name().to_str().and_then(Entry::parse) {
            entries.push(entry);
        }
    }
    sort(&mut entries);
    Ok(entries)
}

fn sort(entries: &mut [Entry]) {
    entries.sort_by(|left, right| (left.rank, &left.id).cmp(&(right.rank, &right.id)));
}

/// Place `entry` among `entries`, unless it is already there.
pub(super) fn with_entry(mut entries: Vec<Entry>, entry: &Entry) -> Vec<Entry> {
    if !entries.iter().any(|queued| queued.id == entry.id) {
        entries.push(entry.clone());
        sort(&mut entries);
    }
    entries
}

/// Where `id` stands in `queue`, counted from the head; the head when it is
/// not listed.
pub(super) fn position(queue: &[Entry], id: &str) -> u32 {
    queue
        .iter()
        .position(|entry| entry.id == id)
        .map_or(0, |index| index as u32)
}

/// Whether another request's ticket counts now, and if so the slots the
/// last plan gave it. A ticket whose owner is gone is deleted. Call only
/// under `queue.lock`.
pub(super) fn ready(root: &Path, entry: &Entry, now: SystemTime) -> Option<u128> {
    match owner_alive(&waiters_dir(root).join(&entry.id)) {
        Some(true) => {}
        Some(false) => {
            remove(root, entry);
            return None;
        }
        None => return None,
    }
    fs::File::open(queue_dir(root).join(entry.name()))
        .ok()
        .and_then(|mut file| read_state(&mut file))
        .filter(|state| state.fresh(now))
        .map(|state| state.slots)
}

/// The slots the queue's woken tickets are about to claim, when no live
/// ticket is owed a plan: the other free slots are then anybody's, and a
/// release has nobody to wake. `None` when a live ticket has no
/// assignment, a ticket's owner is dead, or the queue cannot be read;
/// that takes a plan under `queue.lock`, which also deletes the dead
/// ticket. Reads without the lock, so it deletes nothing itself; a stale
/// wake is skipped, as a plan skips it.
pub(super) fn claimed_slots(root: &Path, now: SystemTime) -> Option<u128> {
    let mut claimed = 0;
    for entry in list(root).ok()? {
        if owner_alive(&waiters_dir(root).join(&entry.id)) != Some(true) {
            return None;
        }
        let mut file = match fs::File::open(queue_dir(root).join(entry.name())) {
            Ok(file) => file,
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => continue,
            Err(_) => return None,
        };
        let state = read_state(&mut file)?;
        if !state.fresh(now) {
            continue;
        }
        if state.woken == 0 || state.slots == 0 {
            return None;
        }
        claimed |= state.slots;
    }
    Some(claimed)
}

/// `Some(false)` when nothing holds the lock at `path` or the file is gone;
/// `None` when it cannot be probed.
fn owner_alive(path: &Path) -> Option<bool> {
    probe_owner(fs::File::open(path))
}

fn probe_owner(opened: std::io::Result<fs::File>) -> Option<bool> {
    let file = match opened {
        Ok(file) => file,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Some(false),
        Err(_) => return None,
    };
    match file.try_lock_shared() {
        Ok(()) => Some(false),
        Err(fs::TryLockError::WouldBlock) => Some(true),
        Err(fs::TryLockError::Error(_)) => None,
    }
}

/// Create and lock the file that says a waiter is alive.
fn waiter_lock(path: &Path) -> Result<fs::File> {
    let owner = fs::OpenOptions::new()
        .read(true)
        .write(true)
        .create_new(true)
        .open(path)?;
    if let Err(error) = owner.try_lock() {
        let _ = fs::remove_file(path);
        anyhow::bail!("waiter lock unavailable: {error}");
    }
    Ok(owner)
}

fn remove(root: &Path, entry: &Entry) {
    let _ = fs::remove_file(queue_dir(root).join(entry.name()));
    let _ = fs::remove_file(waiters_dir(root).join(&entry.id));
}

/// What `entry`'s ticket says. Call only under `queue.lock`.
#[cfg(test)]
pub(super) fn state(root: &Path, entry: &Entry) -> Option<State> {
    fs::File::open(queue_dir(root).join(entry.name()))
        .ok()
        .and_then(|mut file| read_state(&mut file))
}

/// How often `entry` has been passed. Call only under `queue.lock`.
pub(super) fn passes(root: &Path, entry: &Entry) -> u32 {
    fs::File::open(queue_dir(root).join(entry.name()))
        .ok()
        .and_then(|mut file| read_state(&mut file))
        .map_or(0, |state| state.passes)
}

/// Count one more pass of `entry`. Call only under `queue.lock`.
pub(super) fn record_pass(root: &Path, entry: &Entry) -> Result<()> {
    let mut file = fs::OpenOptions::new()
        .read(true)
        .write(true)
        .open(queue_dir(root).join(entry.name()))?;
    let mut state = read_state(&mut file).unwrap_or_default();
    state.passes = state.passes.saturating_add(1);
    write_state(&mut file, state)
}

/// What [`plan`] gives the request it was asked about.
#[derive(Debug, PartialEq, Eq)]
pub(super) struct Admitted {
    /// The slots to take now.
    pub(super) slots: Vec<u32>,
    /// The first ticket, when it was waiting and this request passes it.
    pub(super) passed: Option<Entry>,
    /// Free test slots no ticket wants, when asked for.
    pub(super) spare: Vec<u32>,
}

/// Why [`plan`] gave the request it was asked about nothing yet.
#[derive(Debug, PartialEq, Eq)]
pub(super) struct Waiting {
    /// Free slots the first ticket, a test, reserves. A compile counts them
    /// as slots tests hold.
    pub(super) saved_for_tests: u32,
}

/// Hand `free` slots to the tickets in `queue`, which is in rank order and
/// holds `me`, and say what `me` gets, or why it waits.
///
/// `ready` is asked only about other tickets that would take slots or would
/// be first, and says which slots a ticket was given before, which it keeps
/// when they are still free; `passes` is asked only about the first ticket
/// when it does not fit.
/// With `spare`, the tickets after `me` take their slots too, and the test
/// slots left over are spare.
pub(super) fn plan(
    queue: &[Entry],
    me: &str,
    free: &[u32],
    reserve: u32,
    budget: u32,
    spare: bool,
    ready: impl FnMut(&Entry) -> Option<u128>,
    passes: impl FnMut(&Entry) -> u32,
) -> Result<Admitted, Waiting> {
    let assigned = assign(queue, Some(me), free, reserve, budget, spare, ready, passes);
    let Some((_, slots)) = assigned.admitted.iter().find(|(entry, _)| entry.id == me) else {
        return Err(Waiting {
            saved_for_tests: assigned.saved_for_tests,
        });
    };
    let spare = if spare {
        assigned
            .left
            .into_iter()
            .filter(|&index| Kind::Test.uses(index, reserve))
            .collect()
    } else {
        Vec::new()
    };
    Ok(Admitted {
        slots: slots.clone(),
        passed: assigned.passed.cloned(),
        spare,
    })
}

/// What [`assign`] hands out.
struct Assigned<'a> {
    /// The tickets that take slots now, in rank order, with their slots.
    admitted: Vec<(&'a Entry, Vec<u32>)>,
    /// Free slots no admitted ticket took.
    left: Vec<u32>,
    /// The first ticket, when it did not fit and a later one took slots.
    passed: Option<&'a Entry>,
    /// Free slots the first ticket, a test, reserves.
    saved_for_tests: u32,
}

/// Hand `free` slots to the tickets in `queue` in rank order. With `me`,
/// stop once `me` has its slots or does not fit, unless `through`; without
/// `me`, every ticket is another's and all are planned.
fn assign<'a>(
    queue: &'a [Entry],
    me: Option<&str>,
    free: &[u32],
    reserve: u32,
    budget: u32,
    through: bool,
    mut ready: impl FnMut(&Entry) -> Option<u128>,
    mut passes: impl FnMut(&Entry) -> u32,
) -> Assigned<'a> {
    let mut available = free.to_vec();
    let mut saved_for_tests = 0;
    // The first ticket that counts, and whether it got its slots.
    let mut first: Option<(&Entry, bool)> = None;
    let mut admitted = Vec::new();
    let mut mine_done = false;
    for entry in queue {
        if mine_done && !through {
            break;
        }
        let is_me = me == Some(entry.id.as_str());
        let fits = fits(&available, entry.kind, entry.need, reserve);
        let prior = if !is_me && (fits || first.is_none()) {
            match ready(entry) {
                Some(prior) => prior,
                None => continue,
            }
        } else {
            0
        };
        let fit = fits.then(|| take(&available, entry.kind, entry.need, reserve, prior));
        let is_first = first.is_none();
        match fit {
            Some(slots) => {
                available.retain(|index| !slots.contains(index));
                if is_first {
                    first = Some((entry, true));
                }
                if is_me {
                    mine_done = true;
                }
                admitted.push((entry, slots));
            }
            None if is_me => break,
            None if is_first => {
                first = Some((entry, false));
                if passes(entry) >= budget {
                    let before = available.len();
                    available.retain(|&index| !entry.kind.uses(index, reserve));
                    if entry.kind == Kind::Test {
                        saved_for_tests = (before - available.len()) as u32;
                    }
                }
            }
            None => {}
        }
    }
    let passed = match first {
        Some((entry, false)) => Some(entry),
        _ => None,
    };
    Assigned {
        admitted,
        left: available,
        passed,
        saved_for_tests,
    }
}

/// Plan for the whole queue after slots were freed, and wake every ticket
/// the plan admits. Called by whoever changed the state: a holder dropping
/// slots, a waiter leaving. Nothing is woken when `queue.lock` stays held
/// for [`LOCK_WAIT`]; the waiters' backstop covers that.
pub(super) fn wake_admitted(root: &Path, pool: u32) {
    // With every live ticket already assigned its slots there is nobody to
    // wake, and no lock to take.
    if claimed_slots(root, SystemTime::now()).is_some() {
        return;
    }
    let Ok(Some(queue_lock)) = lock(root, RELEASE_WAIT, LOCK_WAIT) else {
        return;
    };
    let held = std::time::Instant::now();
    wake_planned(root, pool);
    drop(queue_lock);
    super::admission_stats::lock_held(held.elapsed());
}

/// [`wake_admitted`]'s plan and wakes. Call only under `queue.lock`.
fn wake_planned(root: &Path, pool: u32) {
    let Ok(queue) = list(root) else {
        return;
    };
    let free: Vec<u32> = (0..pool)
        .filter(|index| {
            super::slot_is_held(&super::permits_dir(root).join(index.to_string())) == Some(false)
        })
        .collect();
    let now = SystemTime::now();
    let assigned = assign(
        &queue,
        None,
        &free,
        super::reserve_for(pool),
        pass_budget(pool),
        true,
        |entry| ready(root, entry, now),
        |entry| passes(root, entry),
    );
    for (entry, slots) in &assigned.admitted {
        if let Some(first) = assigned.passed
            && let Err(error) = record_pass(root, first)
        {
            tracing::debug!("could not count a pass of the first waiter: {error:#}");
        }
        wake(root, entry, now, slots);
    }
}

/// Tell `entry`'s owner that `slots` are its. The first wake since the
/// owner last looked is the one its [`STALE_AFTER`] runs from; the slots
/// are the latest plan's. Call only under `queue.lock`.
pub(super) fn wake(root: &Path, entry: &Entry, now: SystemTime, slots: &[u32]) {
    if let Ok(mut file) = fs::OpenOptions::new()
        .read(true)
        .write(true)
        .open(queue_dir(root).join(entry.name()))
    {
        let mut state = read_state(&mut file).unwrap_or_default();
        let mask = slot_mask(slots);
        if state.woken == 0 || state.slots != mask {
            if state.woken == 0 {
                state.woken = millis(now);
            }
            state.slots = mask;
            let _ = write_state(&mut file, state);
        }
    }
    Word::open(&waiters_dir(root).join(&entry.id)).bump_one();
}

/// Whether `available` has `need` slots that `kind` can use.
fn fits(available: &[u32], kind: Kind, need: u32, reserve: u32) -> bool {
    available
        .iter()
        .filter(|&&index| kind.uses(index, reserve))
        .count()
        >= need as usize
}

/// `need` slots of `available` that `kind` can use: those in `prior`
/// first, so a ticket keeps what an earlier plan gave it, then the lowest.
/// Call only when [`fits`].
fn take(available: &[u32], kind: Kind, need: u32, reserve: u32, prior: u128) -> Vec<u32> {
    let usable = |&index: &u32| kind.uses(index, reserve);
    let in_prior = |&index: &u32| index < 128 && prior & (1u128 << index) != 0;
    let kept: Vec<u32> = available
        .iter()
        .copied()
        .filter(usable)
        .filter(in_prior)
        .take(need as usize)
        .collect();
    let filled = available
        .iter()
        .copied()
        .filter(usable)
        .filter(|index| !kept.contains(index))
        .take(need as usize - kept.len());
    let mut slots: Vec<u32> = kept.iter().copied().chain(filled).collect();
    slots.sort_unstable();
    slots
}

/// A waiting request's place in the queue. Dropping it leaves the queue.
pub(super) struct Ticket {
    root: PathBuf,
    pool: u32,
    entry: Entry,
    state: fs::File,
    /// The counter in `waiters/<id>` that a planner bumps to wake the owner.
    word: Word,
    /// The counter when the owner last looked, under `queue.lock`. A wake
    /// after that is one the owner has not acted on.
    seen: u32,
    // Declared last: the lock is released after both files are unlinked.
    _owner: fs::File,
    wake: bool,
}

impl Ticket {
    /// Queue `entry` in a pool of `pool` slots. Call only under `queue.lock`,
    /// so no planner sees the ticket before its owner holds it.
    pub(super) fn create(root: &Path, entry: Entry, now: SystemTime, pool: u32) -> Result<Self> {
        fs::create_dir_all(queue_dir(root))?;
        fs::create_dir_all(waiters_dir(root))?;
        let owner = waiter_lock(&waiters_dir(root).join(&entry.id))?;
        let word = Word::open(&waiters_dir(root).join(&entry.id));
        // From here on, dropping the ticket removes both files.
        let state = fs::OpenOptions::new()
            .read(true)
            .write(true)
            .create_new(true)
            .open(queue_dir(root).join(entry.name()));
        let state = match state {
            Ok(state) => state,
            Err(error) => {
                let _ = fs::remove_file(waiters_dir(root).join(&entry.id));
                return Err(error.into());
            }
        };
        let seen = word.seen();
        let mut ticket = Self {
            root: root.to_path_buf(),
            pool,
            entry,
            state,
            word,
            seen,
            _owner: owner,
            wake: false,
        };
        write_state(
            &mut ticket.state,
            State {
                passes: 0,
                seen: millis(now),
                woken: 0,
                slots: 0,
            },
        )?;
        ticket.wake = true;
        Ok(ticket)
    }

    pub(super) fn entry(&self) -> &Entry {
        &self.entry
    }

    /// Note that the owner looked at `now`, asking for `need` slots. Call only
    /// under `queue.lock`.
    pub(super) fn refresh(&mut self, need: u32, now: SystemTime) -> Result<()> {
        if need != self.entry.need {
            let renamed = Entry {
                need,
                ..self.entry.clone()
            };
            fs::rename(
                queue_dir(&self.root).join(self.entry.name()),
                queue_dir(&self.root).join(renamed.name()),
            )?;
            self.entry = renamed;
        }
        let mut state = read_state(&mut self.state).unwrap_or_default();
        state.seen = millis(now);
        state.woken = 0;
        state.slots = 0;
        self.seen = self.word.seen();
        write_state(&mut self.state, state)
    }

    /// The slots the last plan gave this ticket, when a planner woke it for
    /// them and it has not looked since. Call only under `queue.lock`.
    pub(super) fn assigned(&mut self) -> Option<Vec<u32>> {
        let state = read_state(&mut self.state)?;
        (state.woken != 0 && state.slots != 0).then(|| mask_slots(state.slots))
    }

    /// Sleep until a planner wakes this ticket or `limit` elapses.
    pub(super) fn park(&self, limit: Duration) -> Wake {
        self.word.wait(self.seen, limit)
    }

    /// Leave the queue after taking slots. Nothing changed for the other
    /// waiters that the slot releases did not already tell them.
    pub(super) fn admitted(mut self) {
        self.wake = false;
    }
}

impl Drop for Ticket {
    fn drop(&mut self) {
        let _ = fs::remove_file(queue_dir(&self.root).join(self.entry.name()));
        let _ = fs::remove_file(waiters_dir(&self.root).join(&self.entry.id));
        if self.wake {
            // A waiter that gives up can free slots it was reserving.
            wake_admitted(&self.root, self.pool);
            super::permit_wait::notify(&self.root);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::cell::RefCell;

    #[test]
    fn lock_counts_every_try_and_a_wait_that_runs_out() {
        let dir = tempfile::tempdir().unwrap();
        let _ = super::super::admission_stats::take();
        let held = lock(dir.path(), Duration::ZERO, LOCK_WAIT)
            .unwrap()
            .unwrap();
        let stats = super::super::admission_stats::take();
        assert_eq!((stats.lock_attempts, stats.lock_gave_up), (1, 0));
        // A second handle on the path cannot take the lock while `held` lives.
        let wait = Duration::from_millis(2);
        assert!(lock(dir.path(), wait, LOCK_WAIT).unwrap().is_none());
        let stats = super::super::admission_stats::take();
        assert!(stats.lock_attempts >= 2, "{stats:?}");
        assert_eq!(stats.lock_gave_up, 1);
        // `None` is returned only once the whole allowance has elapsed.
        assert!(stats.lock_wait_us >= 2000, "{stats:?}");
        drop(held);
    }

    #[test]
    fn a_word_that_moves_restarts_the_stale_clock_and_one_that_stands_still_runs_it_out() {
        let ms = Duration::from_millis;
        let start = std::time::Instant::now();
        let stale = ms(100);
        let mut turnover = Turnover {
            seen: 3,
            changed: start,
        };
        turnover.observe(3, start + ms(60));
        assert_eq!(turnover.left(start + ms(60), stale), ms(40), "unchanged");
        turnover.observe(4, start + ms(60));
        assert_eq!(turnover.left(start + ms(60), stale), ms(100), "moved");
        assert_eq!(turnover.left(start + ms(160), stale), Duration::ZERO);
        assert_eq!(turnover.left(start + ms(500), stale), Duration::ZERO);
    }

    #[test]
    fn a_waiter_outlasts_a_lock_that_keeps_changing_hands() {
        let dir = tempfile::tempdir().unwrap();
        let held = lock(dir.path(), Duration::ZERO, LOCK_WAIT)
            .unwrap()
            .unwrap();
        let path = lock_wake_path(dir.path());
        // Six times `stale` of turnover, then none.
        let stale = Duration::from_millis(100);
        let bumper = std::thread::spawn(move || {
            let word = Word::open(&path);
            let until = std::time::Instant::now() + stale * 6;
            while std::time::Instant::now() < until {
                std::thread::sleep(Duration::from_millis(5));
                word.bump_one();
            }
        });
        let _ = super::super::admission_stats::take();
        let started = std::time::Instant::now();
        assert!(
            lock(dir.path(), Duration::from_secs(30), stale)
                .unwrap()
                .is_none()
        );
        let elapsed = started.elapsed();
        bumper.join().unwrap();
        let stats = super::super::admission_stats::take();
        assert_eq!(stats.lock_gave_up, 1, "{stats:?}");
        assert!(
            elapsed >= stale * 6,
            "turnover kept it waiting: {elapsed:?}"
        );
        assert!(
            elapsed < Duration::from_secs(30),
            "the lock standing still ended the wait"
        );
        drop(held);
    }

    #[test]
    fn a_waiter_that_leaves_passes_its_wake_without_moving_the_word() {
        let dir = tempfile::tempdir().unwrap();
        let held = lock(dir.path(), Duration::ZERO, LOCK_WAIT)
            .unwrap()
            .unwrap();
        let word = Word::open(&lock_wake_path(dir.path()));
        let before = word.seen();
        let stale = Duration::from_millis(50);
        let waiters: Vec<_> = (0..2)
            .map(|_| {
                let root = dir.path().to_path_buf();
                std::thread::spawn(move || {
                    lock(&root, Duration::from_secs(30), stale)
                        .unwrap()
                        .is_none()
                })
            })
            .collect();
        for waiter in waiters {
            assert!(waiter.join().unwrap(), "gave up on a kept lock");
        }
        assert_eq!(
            word.seen(),
            before,
            "a passed wake is not a change of hands"
        );
        drop(held);
        assert_ne!(word.seen(), before, "a drop is");
    }

    #[test]
    fn a_passed_wake_ends_a_sleep_as_an_unchanged_word() {
        let dir = tempfile::tempdir().unwrap();
        let path = lock_wake_path(dir.path());
        let word = Word::open(&path);
        let seen = word.seen();
        let sleeper =
            std::thread::spawn(move || Word::open(&path).wait(seen, Duration::from_secs(30)));
        while !sleeper.is_finished() {
            std::thread::sleep(Duration::from_millis(5));
            word.pass_one();
        }
        let woke = sleeper.join().unwrap();
        assert!(matches!(woke, Wake::Slice | Wake::Unknown), "{woke:?}");
        assert_eq!(word.seen(), seen);
    }

    #[test]
    fn a_waiter_sleeps_a_slice_where_a_drop_wakes_it_and_backs_off_elsewhere() {
        let left = Duration::from_secs(1);
        assert_eq!(lock_slice(true, 0, left), Duration::from_millis(50));
        assert_eq!(lock_slice(true, 9, left), Duration::from_millis(50));
        assert_eq!(lock_slice(false, 0, left), Duration::from_micros(200));
        assert_eq!(lock_slice(false, 1, left), Duration::from_micros(400));
        assert_eq!(lock_slice(false, 3, left), Duration::from_micros(1600));
        assert_eq!(lock_slice(false, 9, left), Duration::from_millis(5));
        let left = Duration::from_micros(300);
        assert_eq!(lock_slice(true, 0, left), left, "never past the allowance");
        assert_eq!(lock_slice(false, 4, left), left);
    }

    #[test]
    fn position_counts_the_tickets_ahead() {
        let queue = vec![
            entry(1, Kind::Compile, 1, "a"),
            entry(2, Kind::Test, 1, "b"),
            entry(3, Kind::Compile, 1, "c"),
        ];
        assert_eq!(position(&queue, "a"), 0);
        assert_eq!(position(&queue, "b"), 1);
        assert_eq!(position(&queue, "c"), 2);
        assert_eq!(position(&queue, "d"), 0, "an unlisted ticket looks at once");
    }

    #[cfg(target_os = "linux")]
    #[test]
    fn a_held_lock_is_tried_once_per_slice_not_polled() {
        let dir = tempfile::tempdir().unwrap();
        let held = lock(dir.path(), Duration::ZERO, LOCK_WAIT)
            .unwrap()
            .unwrap();
        let _ = super::super::admission_stats::take();
        let wait = LOCK_SLICE * 4;
        assert!(lock(dir.path(), wait, LOCK_WAIT).unwrap().is_none());
        let stats = super::super::admission_stats::take();
        // One try per slice and one when the allowance runs out. Polling at
        // `LOCK_POLL` would make a thousand.
        assert!(
            (2..=6).contains(&stats.lock_attempts),
            "{} tries in {wait:?}",
            stats.lock_attempts
        );
        drop(held);
    }

    #[cfg(target_os = "linux")]
    #[test]
    fn dropping_the_lock_hands_it_to_a_waiter_without_a_poll() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path().to_path_buf();
        let held = lock(&root, Duration::ZERO, LOCK_WAIT).unwrap().unwrap();
        let waiter = std::thread::spawn(move || {
            let _ = super::super::admission_stats::take();
            let taken = lock(&root, Duration::from_secs(5), LOCK_WAIT).unwrap();
            (taken.is_some(), super::super::admission_stats::take())
        });
        // Long enough for the waiter to be asleep on the word, short enough
        // that its slice has not run out.
        std::thread::sleep(LOCK_SLICE / 2);
        let dropped = std::time::Instant::now();
        drop(held);
        let (taken, stats) = waiter.join().unwrap();
        assert!(taken);
        assert!(
            stats.lock_attempts <= 2,
            "{} tries; the drop must wake the waiter, not its slice",
            stats.lock_attempts
        );
        assert!(
            dropped.elapsed() < LOCK_SLICE,
            "woken after {:?}; the drop must wake the waiter before its slice ends",
            dropped.elapsed()
        );
    }

    fn entry(rank: u64, kind: Kind, need: u32, id: &str) -> Entry {
        Entry {
            rank,
            kind,
            need,
            id: id.into(),
        }
    }

    fn at(ms: u64) -> SystemTime {
        UNIX_EPOCH + Duration::from_millis(ms)
    }

    /// Plan with every other ticket ready and never passed.
    fn plan_all_ready(queue: &[Entry], me: &str, free: &[u32]) -> Result<Admitted, Waiting> {
        plan(queue, me, free, 1, 4, false, |_| Some(0), |_| 0)
    }

    #[test]
    fn a_ticket_name_round_trips() {
        let queued = entry(1_793_351_028_000, Kind::Test, 3, "9f3a00c1");
        assert_eq!(queued.name(), "1793351028000-t-3-9f3a00c1");
        assert_eq!(Entry::parse(&queued.name()), Some(queued));
        assert_eq!(
            Entry::parse("5-c-1-ab"),
            Some(entry(5, Kind::Compile, 1, "ab"))
        );
    }

    #[test]
    fn names_that_are_not_tickets_are_rejected() {
        for name in [
            "",
            "5",
            "5-c",
            "5-c-1",
            "5-c-1-",
            "x-c-1-ab",
            "5-x-1-ab",
            "5-c-0-ab",
            "5-c-x-ab",
            "5-c-1-a.b",
            "5-c-1-a-b",
            "-5-c-1-ab",
        ] {
            assert_eq!(Entry::parse(name), None, "{name:?}");
        }
    }

    #[test]
    fn new_ids_are_distinct_ticket_ids() {
        let first = Entry::new(1, Kind::Compile, 1);
        let second = Entry::new(1, Kind::Compile, 1);
        assert_ne!(first.id, second.id);
        assert_eq!(first.id.len(), 16);
        assert_eq!(Entry::parse(&first.name()), Some(first));
    }

    #[test]
    fn fallback_ids_keep_the_process_and_sequence_distinct() {
        let first = fallback_id(17, 3);
        assert!(valid_id(&first));
        assert_ne!(first, fallback_id(18, 3));
        assert_ne!(first, fallback_id(17, 4));
        assert_ne!(fallback_id(1, 0x100), fallback_id(0x11, 0));
    }

    #[test]
    fn an_unreadable_owner_is_not_a_dead_owner() {
        assert_eq!(
            probe_owner(Err(std::io::ErrorKind::NotFound.into())),
            Some(false)
        );
        assert_eq!(
            probe_owner(Err(std::io::ErrorKind::PermissionDenied.into())),
            None
        );
        assert_eq!(probe_owner(Err(std::io::ErrorKind::Other.into())), None);
    }

    #[test]
    fn a_foreground_request_ranks_ten_seconds_ahead() {
        assert_eq!(rank(at(100_000), Priority::Background), 100_000);
        assert_eq!(rank(at(100_000), Priority::Foreground), 90_000);
        assert_eq!(rank(at(5_000), Priority::Foreground), 0, "saturates");
        assert_eq!(
            rank(UNIX_EPOCH - Duration::from_secs(1), Priority::Background),
            0
        );
        // Waiting raises priority: a background request that has waited the
        // head start goes before a foreground one that arrives after.
        assert!(rank(at(100_000), Priority::Background) < rank(at(110_001), Priority::Foreground));
        assert!(rank(at(100_000), Priority::Background) > rank(at(109_999), Priority::Foreground));
    }

    #[test]
    fn the_pass_budget_is_one_pass_per_slot() {
        assert_eq!(pass_budget(1), 1);
        assert_eq!(pass_budget(18), 18);
    }

    #[test]
    fn tests_use_only_slots_above_the_reserve() {
        assert!(Kind::Compile.uses(0, 2));
        assert!(Kind::Compile.uses(5, 2));
        assert!(!Kind::Test.uses(1, 2));
        assert!(Kind::Test.uses(2, 2));
    }

    #[test]
    fn a_ticket_keeps_the_slots_an_earlier_plan_gave_it() {
        let queue = [
            entry(1, Kind::Test, 2, "told"),
            entry(2, Kind::Test, 1, "me"),
        ];
        // Told of 5 and 7; 3 freed since. It keeps 5 and 7, so the request
        // behind gets 3 instead of 7.
        let admitted = plan(
            &queue,
            "me",
            &[3, 5, 7],
            0,
            4,
            false,
            |_| Some(slot_mask(&[5, 7])),
            |_| 0,
        )
        .unwrap();
        assert_eq!(admitted.slots, [3]);
        // A slot it was told of that is held again is replaced by the lowest.
        assert_eq!(
            take(&[3, 5, 7], Kind::Test, 2, 0, slot_mask(&[7, 9])),
            [3, 7]
        );
        assert_eq!(take(&[3, 5, 7], Kind::Test, 2, 0, 0), [3, 5]);
        assert_eq!(
            take(&[1, 3], Kind::Test, 1, 2, slot_mask(&[1])),
            [3],
            "a reserve slot is not a test's"
        );
    }

    #[test]
    fn a_slot_mask_round_trips_and_has_no_bit_past_127() {
        assert_eq!(slot_mask(&[]), 0);
        assert_eq!(slot_mask(&[0, 2, 127]), 1 | 4 | (1 << 127));
        assert_eq!(mask_slots(1 | 4 | (1 << 127)), [0, 2, 127]);
        assert_eq!(
            slot_mask(&[1, 128]),
            0,
            "a slot without a bit gives up the mask"
        );
    }

    #[test]
    fn a_wake_records_the_slots_and_a_look_clears_them() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path().join("scheduler");
        let now = SystemTime::now();
        let mut ticket = Ticket::create(&root, Entry::new(1, Kind::Test, 2), now, 4).unwrap();
        assert_eq!(ticket.assigned(), None, "nothing planned yet");
        wake(&root, ticket.entry(), now, &[2, 3]);
        assert_eq!(ticket.assigned(), Some(vec![2, 3]));
        wake(&root, ticket.entry(), now, &[1, 3]);
        assert_eq!(ticket.assigned(), Some(vec![1, 3]), "the latest plan's");
        ticket.refresh(2, now).unwrap();
        assert_eq!(ticket.assigned(), None, "a look consumes the assignment");
        ticket.admitted();
    }

    #[test]
    fn the_claimed_slots_are_those_of_woken_live_tickets_and_none_while_one_is_owed_a_plan() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path().join("scheduler");
        let now = SystemTime::now();
        assert_eq!(claimed_slots(&root, now), Some(0), "nothing queued");
        let first = Ticket::create(&root, Entry::new(1, Kind::Test, 2), now, 4).unwrap();
        assert_eq!(claimed_slots(&root, now), None, "a ticket with no plan");
        wake(&root, first.entry(), now, &[2, 3]);
        assert_eq!(claimed_slots(&root, now), Some(0b1100));
        let second = Ticket::create(&root, Entry::new(2, Kind::Compile, 1), now, 4).unwrap();
        assert_eq!(claimed_slots(&root, now), None, "the second has no plan");
        wake(&root, second.entry(), now, &[0]);
        assert_eq!(claimed_slots(&root, now), Some(0b1101));
        let later = now + STALE_AFTER;
        assert_eq!(
            claimed_slots(&root, later),
            Some(0),
            "stale wakes are skipped"
        );
        let gone = Entry::new(3, Kind::Compile, 1);
        fs::write(queue_dir(&root).join(gone.name()), b"").unwrap();
        assert_eq!(
            claimed_slots(&root, now),
            None,
            "a dead owner is left to a plan"
        );
        let _alive = waiter_lock(&waiters_dir(&root).join(&gone.id)).unwrap();
        assert_eq!(
            claimed_slots(&root, now),
            None,
            "a live ticket with no state"
        );
        drop(second);
        first.admitted();
    }

    #[test]
    fn a_woken_ticket_counts_for_two_seconds_and_an_unwoken_one_always() {
        let told = State {
            passes: 0,
            seen: 10_000,
            woken: 10_000,
            slots: 0,
        };
        assert!(told.fresh(at(10_000)));
        assert!(told.fresh(at(11_999)));
        assert!(!told.fresh(at(12_000)));
        assert!(told.fresh(at(9_000)), "a clock step back keeps it");
        let waiting = State {
            passes: 0,
            seen: 10_000,
            woken: 0,
            slots: 0,
        };
        assert!(waiting.fresh(at(12_000)));
        assert!(waiting.fresh(at(u64::MAX / 2)));
    }

    #[test]
    fn a_ticket_state_parses_with_and_without_the_later_fields() {
        assert_eq!(
            State::parse("3 10000 12000 00000000000000000000000000000005"),
            Some(State {
                passes: 3,
                seen: 10_000,
                woken: 12_000,
                slots: 0b101,
            })
        );
        assert_eq!(
            State::parse("3 10000 12000"),
            Some(State {
                passes: 3,
                seen: 10_000,
                woken: 12_000,
                slots: 0,
            })
        );
        assert_eq!(
            State::parse("3 10000"),
            Some(State {
                passes: 3,
                seen: 10_000,
                woken: 0,
                slots: 0,
            })
        );
        assert_eq!(State::parse("3"), None);
        assert_eq!(State::parse("x 1"), None);
        assert_eq!(State::parse("1 x"), None);
        assert_eq!(State::parse("1 2 x"), None);
        assert_eq!(State::parse("1 2 3 x"), None);
    }

    #[test]
    fn with_entry_places_a_new_entry_by_rank_once() {
        let queue = vec![
            entry(1, Kind::Compile, 1, "a"),
            entry(3, Kind::Compile, 1, "c"),
        ];
        let me = entry(2, Kind::Compile, 1, "b");
        let placed = with_entry(queue, &me);
        let ids: Vec<_> = placed.iter().map(|entry| entry.id.as_str()).collect();
        assert_eq!(ids, ["a", "b", "c"]);
        assert_eq!(with_entry(placed.clone(), &me), placed);
        let tied = with_entry(vec![entry(2, Kind::Compile, 1, "z")], &me);
        assert_eq!(tied[0].id, "b", "ties break on the id");
    }

    #[test]
    fn the_only_request_takes_the_lowest_free_slots() {
        let me = entry(1, Kind::Compile, 2, "me");
        let admitted = plan_all_ready(std::slice::from_ref(&me), "me", &[1, 2, 3]).unwrap();
        assert_eq!(admitted.slots, [1, 2]);
        assert_eq!(admitted.passed, None);
        assert!(admitted.spare.is_empty());
        let test = entry(1, Kind::Test, 2, "me");
        let admitted = plan(&[test], "me", &[0, 1, 2], 1, 4, false, |_| Some(0), |_| 0).unwrap();
        assert_eq!(admitted.slots, [1, 2], "a test skips the reserve");
        assert_eq!(
            plan_all_ready(&[me], "me", &[1]),
            Err(Waiting { saved_for_tests: 0 })
        );
    }

    #[test]
    fn a_ticket_ahead_that_fits_goes_first() {
        let queue = [
            entry(1, Kind::Compile, 1, "ahead"),
            entry(2, Kind::Compile, 1, "me"),
        ];
        assert_eq!(
            plan_all_ready(&queue, "me", &[4]),
            Err(Waiting { saved_for_tests: 0 })
        );
        let admitted = plan_all_ready(&queue, "me", &[4, 5]).unwrap();
        assert_eq!(admitted.slots, [5]);
        assert_eq!(admitted.passed, None, "the first ticket got its slots");
    }

    #[test]
    fn a_large_first_ticket_is_passed_until_its_budget_is_spent() {
        let queue = [
            entry(1, Kind::Compile, 3, "large"),
            entry(2, Kind::Compile, 1, "me"),
        ];
        let with_passes =
            |passes| plan(&queue, "me", &[0, 1], 0, 2, false, |_| Some(0), |_| passes);
        let admitted = with_passes(0).unwrap();
        assert_eq!(admitted.slots, [0]);
        assert_eq!(admitted.passed, Some(queue[0].clone()));
        assert!(with_passes(1).is_ok());
        assert_eq!(
            with_passes(2),
            Err(Waiting { saved_for_tests: 0 }),
            "the budget is spent: it reserves, and saves nothing for tests"
        );
        assert_eq!(with_passes(3), Err(Waiting { saved_for_tests: 0 }));
    }

    #[test]
    fn a_reserving_test_leaves_compiles_the_reserve() {
        let queue = [
            entry(1, Kind::Test, 3, "test"),
            entry(2, Kind::Compile, 1, "me"),
        ];
        let admitted = plan(&queue, "me", &[0, 2], 1, 0, false, |_| Some(0), |_| 0).unwrap();
        assert_eq!(admitted.slots, [0], "a test cannot use slot 0");
        let queue = [
            entry(1, Kind::Compile, 3, "compile"),
            entry(2, Kind::Test, 1, "me"),
        ];
        assert_eq!(
            plan(&queue, "me", &[0, 2], 1, 0, false, |_| Some(0), |_| 0),
            Err(Waiting { saved_for_tests: 0 }),
            "a reserving compile can use every slot"
        );
    }

    #[test]
    fn a_compile_learns_how_many_slots_a_waiting_test_saves() {
        let queue = [
            entry(1, Kind::Test, 3, "test"),
            entry(2, Kind::Compile, 2, "me"),
        ];
        let with = |passes| {
            plan(
                &queue,
                "me",
                &[0, 2, 3],
                1,
                1,
                false,
                |_| Some(0),
                |_| passes,
            )
        };
        assert_eq!(
            with(1),
            Err(Waiting { saved_for_tests: 2 }),
            "slots 2 and 3 are saved; the reserve alone is too few"
        );
        assert_eq!(
            with(0).unwrap().slots,
            [0, 2],
            "within its budget the test saves nothing"
        );
        let queue = [
            entry(1, Kind::Test, 3, "test"),
            entry(2, Kind::Compile, 1, "me"),
        ];
        let admitted = plan(&queue, "me", &[0, 2, 3], 1, 0, false, |_| Some(0), |_| 0).unwrap();
        assert_eq!(
            admitted.slots,
            [0],
            "a light compile fits beside the saved slots"
        );
    }

    #[test]
    fn tickets_that_are_not_ready_are_skipped() {
        let queue = [
            entry(1, Kind::Compile, 9, "gone"),
            entry(2, Kind::Compile, 1, "stale"),
            entry(3, Kind::Compile, 2, "large"),
            entry(4, Kind::Compile, 1, "me"),
        ];
        let asked = RefCell::new(Vec::new());
        let admitted = plan(
            &queue,
            "me",
            &[0, 1, 2],
            0,
            0,
            false,
            |entry| {
                asked.borrow_mut().push(entry.id.clone());
                (entry.id == "large").then_some(0)
            },
            |_| 0,
        )
        .unwrap();
        assert_eq!(admitted.slots, [2], "the large ticket is first and fits");
        assert_eq!(admitted.passed, None);
        assert_eq!(*asked.borrow(), ["gone", "stale", "large"]);
    }

    #[test]
    fn readiness_is_asked_only_of_tickets_that_matter() {
        let queue = [
            entry(1, Kind::Compile, 1, "first"),
            entry(2, Kind::Compile, 5, "large"),
            entry(3, Kind::Compile, 1, "me"),
            entry(4, Kind::Compile, 1, "after"),
        ];
        let asked = RefCell::new(Vec::new());
        let passes_asked = RefCell::new(0);
        let admitted = plan(
            &queue,
            "me",
            &[0, 1],
            0,
            0,
            false,
            |entry| {
                asked.borrow_mut().push(entry.id.clone());
                Some(0)
            },
            |_| {
                *passes_asked.borrow_mut() += 1;
                0
            },
        )
        .unwrap();
        assert_eq!(admitted.slots, [1]);
        assert_eq!(
            *asked.borrow(),
            ["first"],
            "a later large ticket takes nothing"
        );
        assert_eq!(*passes_asked.borrow(), 0, "the first ticket fit");
    }

    #[test]
    fn a_first_request_that_does_not_fit_waits_without_asking() {
        let queue = [
            entry(1, Kind::Compile, 3, "me"),
            entry(2, Kind::Compile, 1, "small"),
        ];
        let asked = RefCell::new(0);
        let plan = plan(
            &queue,
            "me",
            &[0],
            0,
            0,
            true,
            |_| {
                *asked.borrow_mut() += 1;
                Some(0)
            },
            |_| {
                *asked.borrow_mut() += 1;
                0
            },
        );
        assert_eq!(plan, Err(Waiting { saved_for_tests: 0 }));
        assert_eq!(*asked.borrow(), 0);
    }

    #[test]
    fn spare_test_slots_are_what_every_ticket_leaves() {
        let queue = [
            entry(1, Kind::Test, 2, "ahead"),
            entry(2, Kind::Test, 1, "me"),
            entry(3, Kind::Test, 2, "after"),
            entry(4, Kind::Compile, 1, "compile"),
        ];
        let admitted = plan(
            &queue,
            "me",
            &[0, 1, 2, 3, 4, 5, 6, 7],
            2,
            4,
            true,
            |_| Some(0),
            |_| 0,
        )
        .unwrap();
        assert_eq!(admitted.slots, [4]);
        assert_eq!(
            admitted.spare,
            [7],
            "0 and 1 are the reserve; 6 is the compile's"
        );
        let without = plan(
            &queue,
            "me",
            &[0, 1, 2, 3, 4, 5, 6, 7],
            2,
            4,
            false,
            |_| Some(0),
            |_| 0,
        )
        .unwrap();
        assert!(without.spare.is_empty());
        let asked = RefCell::new(Vec::new());
        plan(
            &queue,
            "me",
            &[2, 3, 4],
            2,
            4,
            false,
            |entry| {
                asked.borrow_mut().push(entry.id.clone());
                Some(0)
            },
            |_| 0,
        )
        .unwrap();
        assert_eq!(
            *asked.borrow(),
            ["ahead"],
            "no spare: tickets after are not read"
        );
    }

    fn root() -> tempfile::TempDir {
        tempfile::tempdir().unwrap()
    }

    #[test]
    fn a_ticket_is_listed_while_held_and_removed_when_dropped() {
        let dir = root();
        assert!(list(dir.path()).unwrap().is_empty(), "no queue yet");
        let queued = entry(7, Kind::Compile, 2, "abc");
        let mut ticket = Ticket::create(dir.path(), queued.clone(), at(5_000), 4).unwrap();
        assert_eq!(ticket.entry(), &queued);
        fs::write(queue_dir(dir.path()).join("not-a-ticket"), b"").unwrap();
        assert_eq!(list(dir.path()).unwrap(), std::slice::from_ref(&queued));
        assert_eq!(
            owner_alive(&waiters_dir(dir.path()).join("abc")),
            Some(true)
        );
        assert!(ready(dir.path(), &queued, at(6_000)).is_some());
        assert!(
            ready(dir.path(), &queued, at(60_000)).is_some(),
            "a ticket nobody woke never goes stale"
        );
        wake(dir.path(), &queued, at(7_000), &[0]);
        assert!(ready(dir.path(), &queued, at(8_999)).is_some());
        assert!(
            ready(dir.path(), &queued, at(9_000)).is_none(),
            "woken, not claimed"
        );
        wake(dir.path(), &queued, at(9_500), &[0]);
        assert!(
            ready(dir.path(), &queued, at(9_600)).is_none(),
            "a second wake does not restart the clock"
        );
        assert_eq!(
            list(dir.path()).unwrap(),
            std::slice::from_ref(&queued),
            "stale is kept"
        );
        ticket.refresh(2, at(9_700)).unwrap();
        assert!(
            ready(dir.path(), &queued, at(12_000)).is_some(),
            "the owner looking makes it count again"
        );
        drop(ticket);
        assert!(list(dir.path()).unwrap().is_empty());
        assert!(!waiters_dir(dir.path()).join("abc").exists());
    }

    #[test]
    fn list_sorts_by_rank_and_reports_an_unreadable_queue() {
        let dir = root();
        let _late =
            Ticket::create(dir.path(), entry(9, Kind::Compile, 1, "late"), at(0), 4).unwrap();
        let _early =
            Ticket::create(dir.path(), entry(3, Kind::Test, 1, "early"), at(0), 4).unwrap();
        let ids: Vec<_> = list(dir.path())
            .unwrap()
            .into_iter()
            .map(|entry| entry.id)
            .collect();
        assert_eq!(ids, ["early", "late"]);
        let file = root();
        fs::write(file.path().join("queue"), b"").unwrap();
        assert!(list(file.path()).is_err());
    }

    #[test]
    fn a_ticket_whose_owner_is_gone_is_deleted() {
        let dir = root();
        let queued = entry(7, Kind::Compile, 1, "dead");
        fs::create_dir_all(queue_dir(dir.path())).unwrap();
        fs::create_dir_all(waiters_dir(dir.path())).unwrap();
        // What a killed owner leaves: both files, and no lock.
        fs::write(queue_dir(dir.path()).join(queued.name()), b"0 5000").unwrap();
        fs::write(waiters_dir(dir.path()).join("dead"), b"").unwrap();
        assert!(ready(dir.path(), &queued, at(5_000)).is_none());
        assert!(list(dir.path()).unwrap().is_empty());
        assert!(!waiters_dir(dir.path()).join("dead").exists());

        // A ticket whose lock file is already gone.
        fs::write(queue_dir(dir.path()).join(queued.name()), b"0 5000").unwrap();
        assert!(ready(dir.path(), &queued, at(5_000)).is_none());
        assert!(list(dir.path()).unwrap().is_empty());
    }

    #[test]
    fn a_live_ticket_with_no_state_is_not_ready() {
        let dir = root();
        let queued = entry(7, Kind::Compile, 1, "blank");
        let _ticket = Ticket::create(dir.path(), queued.clone(), at(5_000), 4).unwrap();
        fs::write(queue_dir(dir.path()).join(queued.name()), b"").unwrap();
        assert!(ready(dir.path(), &queued, at(5_000)).is_none());
        assert_eq!(
            list(dir.path()).unwrap(),
            [queued],
            "its owner still holds it"
        );
    }

    #[test]
    fn refreshing_a_ticket_renames_it_and_keeps_its_passes() {
        let dir = root();
        let queued = entry(7, Kind::Compile, 4, "grow");
        let mut ticket = Ticket::create(dir.path(), queued.clone(), at(1_000), 4).unwrap();
        record_pass(dir.path(), &queued).unwrap();
        record_pass(dir.path(), &queued).unwrap();
        assert_eq!(passes(dir.path(), &queued), 2);

        ticket.refresh(4, at(3_000)).unwrap();
        assert_eq!(
            list(dir.path()).unwrap(),
            std::slice::from_ref(&queued),
            "same need, same name"
        );
        assert!(
            ready(dir.path(), &queued, at(4_000)).is_some(),
            "seen again at 3 s"
        );

        ticket.refresh(2, at(5_000)).unwrap();
        let shrunk = entry(7, Kind::Compile, 2, "grow");
        assert_eq!(ticket.entry(), &shrunk);
        assert_eq!(list(dir.path()).unwrap(), std::slice::from_ref(&shrunk));
        assert_eq!(passes(dir.path(), &shrunk), 2);
        assert_eq!(passes(dir.path(), &queued), 0, "the old name is gone");
        assert!(record_pass(dir.path(), &queued).is_err());
        drop(ticket);
        assert!(list(dir.path()).unwrap().is_empty());
    }

    #[test]
    fn a_taken_name_leaves_no_waiter_lock_behind() {
        let dir = root();
        let queued = entry(7, Kind::Compile, 1, "twice");
        fs::create_dir_all(queue_dir(dir.path())).unwrap();
        fs::write(queue_dir(dir.path()).join(queued.name()), b"").unwrap();
        assert!(Ticket::create(dir.path(), queued, at(0), 4).is_err());
        assert!(!waiters_dir(dir.path()).join("twice").exists());
        let held =
            Ticket::create(dir.path(), entry(1, Kind::Compile, 1, "held"), at(0), 4).unwrap();
        assert!(
            Ticket::create(dir.path(), entry(2, Kind::Compile, 1, "held"), at(0), 4).is_err(),
            "an id another waiter holds"
        );
        assert!(waiters_dir(dir.path()).join("held").exists());
        drop(held);
    }

    #[cfg(target_os = "linux")]
    #[test]
    fn only_a_ticket_that_gives_up_wakes_the_waiters() {
        let dir = root();
        let seen = super::super::permit_wait::snapshot(dir.path());
        Ticket::create(dir.path(), entry(1, Kind::Compile, 1, "admitted"), at(0), 4)
            .unwrap()
            .admitted();
        assert_eq!(super::super::permit_wait::snapshot(dir.path()), seen);
        drop(
            Ticket::create(
                dir.path(),
                entry(1, Kind::Compile, 1, "cancelled"),
                at(0),
                4,
            )
            .unwrap(),
        );
        assert_eq!(
            super::super::permit_wait::snapshot(dir.path()),
            seen.wrapping_add(1)
        );
    }
}
