use super::*;
use std::ffi::OsString;
use std::process::Command;

#[test]
fn an_unset_kache_slice_names_dev_slice() {
    assert_eq!(slice_name(None), Some("dev.slice"));
}

#[test]
fn a_kache_slice_naming_a_slice_unit_is_used_as_given() {
    assert_eq!(
        slice_name(Some(OsStr::new("build-x.slice"))),
        Some("build-x.slice")
    );
}

#[test]
fn an_empty_or_non_slice_kache_slice_disables_the_move() {
    assert_eq!(slice_name(Some(OsStr::new(""))), None);
    assert_eq!(slice_name(Some(OsStr::new("dev"))), None);
    assert_eq!(slice_name(Some(OsStr::new("dev.scope"))), None);
}

#[test]
fn a_non_utf8_kache_slice_disables_the_move() {
    use std::os::unix::ffi::OsStringExt;
    let value = OsString::from_vec(b"d\xffv.slice".to_vec());
    assert_eq!(slice_name(Some(&value)), None);
}

#[test]
fn a_path_through_the_slice_is_inside_it() {
    let cgroup = "0::/user.slice/user-1.slice/user@1.service/dev.slice/run-x.scope\n";
    assert_eq!(in_slice(cgroup, "dev.slice"), Some(true));
}

#[test]
fn a_nested_slice_is_inside_its_parent_and_itself() {
    let cgroup = "0::/user.slice/user@1.service/dev.slice/dev-x.slice/kache-1.scope\n";
    assert_eq!(in_slice(cgroup, "dev.slice"), Some(true));
    assert_eq!(in_slice(cgroup, "dev-x.slice"), Some(true));
}

#[test]
fn a_component_that_only_contains_the_slice_name_is_outside_it() {
    let cgroup = "0::/user.slice/user@1.service/app.slice/xdev.slice/dev.slice.scope\n";
    assert_eq!(in_slice(cgroup, "dev.slice"), Some(false));
}

#[test]
fn a_process_with_no_cgroup_v2_path_has_no_placement() {
    assert_eq!(in_slice("4:cpu:/dev.slice/job\n", "dev.slice"), None);
    assert_eq!(in_slice("", "dev.slice"), None);
}

#[test]
fn the_bus_address_names_the_socket_path() {
    assert_eq!(
        bus_socket(
            Some(OsStr::new("unix:path=/run/user/7/bus,guid=abc")),
            Some(OsStr::new("/elsewhere"))
        ),
        Some(PathBuf::from("/run/user/7/bus"))
    );
    assert_eq!(
        bus_socket(Some(OsStr::new("unix:guid=abc,path=/p/bus")), None),
        Some(PathBuf::from("/p/bus"))
    );
}

#[test]
fn only_the_first_of_several_bus_addresses_is_used() {
    assert_eq!(
        bus_socket(Some(OsStr::new("unix:path=/a;unix:path=/b")), None),
        Some(PathBuf::from("/a"))
    );
    assert_eq!(
        bus_socket(Some(OsStr::new("tcp:host=h;unix:path=/b")), None),
        None
    );
}

#[test]
fn a_bus_address_without_a_unix_path_has_no_socket() {
    for address in ["unix:abstract=/tmp/dbus-x", "tcp:host=h,port=1", ""] {
        assert_eq!(
            bus_socket(Some(OsStr::new(address)), Some(OsStr::new("/run/user/7"))),
            None,
            "{address}"
        );
    }
}

#[test]
fn without_a_bus_address_the_runtime_directory_holds_the_bus() {
    assert_eq!(
        bus_socket(None, Some(OsStr::new("/run/user/7"))),
        Some(PathBuf::from("/run/user/7/bus"))
    );
    assert_eq!(bus_socket(None, Some(OsStr::new(""))), None);
    assert_eq!(bus_socket(None, None), None);
}

/// Expected bytes derived by hand from the D-Bus marshalling rules: strings
/// are a u32 length, the bytes and a NUL, aligned to 4; a struct and a
/// dict entry start on 8; an array's length counts its elements but not the
/// padding before the first, and that padding is present even when empty.
#[cfg(target_endian = "little")]
#[test]
fn the_transient_scope_request_marshals_name_mode_properties_and_no_aux_units() {
    let mut expected: Vec<u8> = Vec::new();
    expected.extend(b"\x07\0\0\0u.scope\0"); // 0..12 s name
    expected.extend(b"\x04\0\0\0fail\0"); // 12..21 s mode
    expected.extend(b"\0\0\0"); // pad to 24
    expected.extend(b"\x63\0\0\0"); // 24..28 a(sv) length 99
    expected.extend(b"\0\0\0\0"); // pad to 32, first struct
    expected.extend(b"\x04\0\0\0PIDs\0"); // 32..41
    expected.extend(b"\x02au\0"); // 41..45 variant signature
    expected.extend(b"\0\0\0"); // pad to 48
    expected.extend(b"\x04\0\0\0"); // 48..52 au length 4
    expected.extend(b"\x07\0\0\0"); // 52..56 pid 7
    expected.extend(b"\x05\0\0\0Slice\0"); // 56..66, already on 8
    expected.extend(b"\x01s\0"); // 66..69
    expected.extend(b"\0\0\0"); // pad to 72
    expected.extend(b"\x07\0\0\0s.slice\0"); // 72..84
    expected.extend(b"\0\0\0\0"); // pad to 88
    expected.extend(b"\x0b\0\0\0CollectMode\0"); // 88..104
    expected.extend(b"\x01s\0"); // 104..107
    expected.extend(b"\0"); // pad to 108
    expected.extend(b"\x12\0\0\0inactive-or-failed\0"); // 108..131
    expected.extend(b"\0"); // pad to 132
    expected.extend(b"\0\0\0\0"); // 132..136 a(sa(sv)) length 0
    assert_eq!(transient_scope("u.scope", "s.slice", 7), expected);
}

#[cfg(target_endian = "little")]
#[test]
fn the_job_removed_signal_names_its_unit_third() {
    let mut body: Vec<u8> = Vec::new();
    body.extend(b"\x09\0\0\0"); // u id
    body.extend(b"\x04\0\0\0/j/9\0"); // o job, ends at 13
    body.extend(b"\0\0\0"); // pad to 16
    body.extend(b"\x07\0\0\0x.scope\0"); // s unit
    body.extend(b"\x04\0\0\0done\0"); // s result
    assert_eq!(job_removed_unit(&body), Some("x.scope"));
    assert_eq!(job_removed_unit(&body[..20]), None);
}

#[test]
fn scope_names_carry_the_pid_and_are_scope_units() {
    let name = scope_name(4242);
    assert!(name.starts_with("kache-4242-"), "{name}");
    assert!(name.ends_with(".scope"), "{name}");
    assert_ne!(name, scope_name(4242));
}

const FIXTURE: &str = "dev_slice::tests::enter_fixture";
/// A slice nested under `dev.slice`, so the moved fixture stays in the tier.
pub(crate) const TEST_SLICE: &str = "dev-kachetest.slice";
/// Below 1000, so the fixture's own value shows whether `enter` raised it.
const BASELINE_OOM: &str = "500";

#[test]
#[ignore = "subprocess fixture: enters the slice, then reports its cgroup and oom_score_adj"]
fn enter_fixture() {
    std::fs::write("/proc/self/oom_score_adj", BASELINE_OOM).unwrap();
    enter();
    let path = crate::cgroup_v2_path(&own_cgroup()).unwrap().to_owned();
    let oom = std::fs::read_to_string("/proc/self/oom_score_adj").unwrap();
    println!("\nfixture-cgroup={path}\nfixture-oom={}", oom.trim());
}

/// The fixture's cgroup v2 path and `oom_score_adj` after `enter`.
fn entered(configure: impl FnOnce(&mut Command)) -> (String, String) {
    let mut command = Command::new(std::env::current_exe().unwrap());
    command.args(["--exact", FIXTURE, "--ignored", "--nocapture"]);
    configure(&mut command);
    let output = command.output().unwrap();
    assert!(output.status.success(), "{output:?}");
    let stdout = String::from_utf8(output.stdout).unwrap();
    let field = |name: &str| {
        stdout
            .lines()
            .find_map(|line| line.strip_prefix(name))
            .unwrap_or_else(|| panic!("no {name} in {stdout:?}"))
            .to_owned()
    };
    (field("fixture-cgroup="), field("fixture-oom="))
}

fn own_path() -> String {
    crate::cgroup_v2_path(&own_cgroup())
        .expect("this test process has a cgroup v2 path")
        .to_owned()
}

/// Why the live move cannot be tested here, or `None` under a systemd user
/// manager reachable on its bus.
pub(crate) fn no_user_manager() -> Option<String> {
    let runtime = std::env::var_os("XDG_RUNTIME_DIR");
    let Some(bus) = bus_socket(
        std::env::var_os("DBUS_SESSION_BUS_ADDRESS").as_deref(),
        runtime.as_deref(),
    ) else {
        return Some("no user bus address in the environment".into());
    };
    if !bus.exists() {
        return Some(format!("no user bus socket at {}", bus.display()));
    }
    let private = Path::new(&runtime.unwrap_or_default()).join("systemd/private");
    if !private.exists() {
        return Some(format!("no systemd user manager at {}", private.display()));
    }
    if crate::cgroup_v2_path(&own_cgroup()).is_none() {
        return Some("no cgroup v2 hierarchy".into());
    }
    None
}

#[test]
fn a_job_outside_the_slice_moves_into_its_own_scope_there_with_oom_score_adj_1000() {
    if let Some(reason) = no_user_manager() {
        eprintln!("skipping: {reason}");
        return;
    }
    let (path, oom) = entered(|command| {
        command.env("KACHE_SLICE", TEST_SLICE);
    });
    let mut components = path.rsplit('/');
    let scope = components.next().unwrap();
    assert!(
        scope.starts_with("kache-") && scope.ends_with(".scope"),
        "{path}"
    );
    assert_eq!(components.next(), Some(TEST_SLICE), "{path}");
    assert_eq!(oom, "1000");
}

#[test]
fn a_job_already_in_the_slice_stays_in_its_group() {
    if let Some(reason) = no_user_manager() {
        eprintln!("skipping: {reason}");
        return;
    }
    let own = own_path();
    let Some(slice) = own.split('/').rfind(|part| part.ends_with(".slice")) else {
        eprintln!("skipping: this process's group {own} is under no slice");
        return;
    };
    let slice = slice.to_owned();
    let (path, oom) = entered(|command| {
        command.env("KACHE_SLICE", &slice);
    });
    assert_eq!(path, own);
    assert_eq!(oom, BASELINE_OOM);
}

#[test]
fn an_empty_kache_slice_leaves_the_job_in_its_group() {
    if let Some(reason) = no_user_manager() {
        eprintln!("skipping: {reason}");
        return;
    }
    let (path, oom) = entered(|command| {
        command.env("KACHE_SLICE", "");
    });
    assert_eq!(path, own_path());
    assert_eq!(oom, BASELINE_OOM);
}

#[test]
fn without_a_user_bus_the_job_stays_in_its_group() {
    let (path, oom) = entered(|command| {
        command
            .env("KACHE_SLICE", TEST_SLICE)
            .env_remove("DBUS_SESSION_BUS_ADDRESS")
            .env_remove("XDG_RUNTIME_DIR");
    });
    assert_eq!(path, own_path());
    assert_eq!(oom, BASELINE_OOM);
}

#[test]
fn a_bus_that_is_not_listening_leaves_the_job_in_its_group() {
    let root = tempfile::tempdir().unwrap();
    let (path, oom) = entered(|command| {
        command.env("KACHE_SLICE", TEST_SLICE).env(
            "DBUS_SESSION_BUS_ADDRESS",
            format!("unix:path={}", root.path().join("bus").display()),
        );
    });
    assert_eq!(path, own_path());
    assert_eq!(oom, BASELINE_OOM);
}
