//! The process's cgroup v2 path, read from the `/proc/<pid>/cgroup` format
//! (Linux `Documentation/admin-guide/cgroup-v2.rst`, "Processes").

/// The path of the unified-hierarchy (`0::`) line, absolute and free of
/// empty, `.` and `..` components. `None` when there is no such line or its
/// path is ambiguous. Whitespace is kept: it is valid in cgroup names.
pub fn cgroup_v2_path(text: &str) -> Option<&str> {
    text.lines().find_map(|line| {
        let mut fields = line.splitn(3, ':');
        let hierarchy = fields.next()?;
        let controllers = fields.next()?;
        // `str::lines` removes the proc line ending. Keep the field itself
        // byte-for-byte: spaces are valid in cgroup directory names.
        let path = fields.next()?;
        if hierarchy == "0" && controllers.is_empty() && path.starts_with('/') {
            valid_cgroup_relative(path).then_some(path)
        } else {
            None
        }
    })
}

fn valid_cgroup_relative(path: &str) -> bool {
    path == "/"
        || path.strip_prefix('/').is_some_and(|path| {
            path.split('/')
                .all(|part| !part.is_empty() && part != "." && part != "..")
        })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn proc_cgroup_parser_rejects_ambiguous_or_escaping_paths() {
        assert_eq!(
            cgroup_v2_path("5:cpu:/legacy\n0::/user.slice/job\n"),
            Some("/user.slice/job")
        );
        assert_eq!(cgroup_v2_path("0::/\n"), Some("/"));
        assert_eq!(cgroup_v2_path("0:cpu:/job\n"), None);
        assert_eq!(cgroup_v2_path("0::relative\n"), None);
        assert_eq!(cgroup_v2_path("0::/job/../escape\n"), None);
        assert_eq!(cgroup_v2_path("0::/job/./here\n"), None);
        assert_eq!(cgroup_v2_path("0::/job//leaf\n"), None);
    }

    #[test]
    fn proc_cgroup_parser_preserves_path_whitespace() {
        assert_eq!(
            cgroup_v2_path("0::/job with trailing space \n"),
            Some("/job with trailing space ")
        );
    }
}
