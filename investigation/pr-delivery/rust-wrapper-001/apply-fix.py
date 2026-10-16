from pathlib import Path
worktree=Path('/Users/viktor/Developer/github/kache-prs/rust-wrapper-001')
p=worktree/'src/args.rs';s=p.read_text()
a=s.index('/// rustc flags that affect only diagnostics formatting or queries')
b=s.index('/// rustc flags that can flip',a)
s=s[:a]+'''/// Diagnostic presentation must agree with the text replayed on a cache hit.
const DIAGNOSTIC_VALUE_FLAGS: &[&str] = &[
    "--error-format",
    "--json",
    "--color",
    "--diagnostic-width",
];

const IGNORED_VALUE_FLAGS: &[&str] = &["--print", "--explain"];
const IGNORED_ATTACHED_PREFIXES: &[&str] = &["--print=", "--explain="];

'''+s[b:]
s=s.replace('    pub outcome_lint_flags: Vec<String>,','    pub outcome_lint_flags: Vec<String>,\n    /// Diagnostic flags in argv order, with separated values joined by `=`.\n    pub diagnostic_flags: Vec<String>,',1)
s=s.replace('            outcome_lint_flags: Vec::new(),','            outcome_lint_flags: Vec::new(),\n            diagnostic_flags: Vec::new(),',1)
a=s.index('                // Diagnostics / lint / query flags: never change the artifact,')
b=s.index('                _ if IGNORED_VALUE_FLAGS.contains',a)
s=s[:a]+'''                _ if DIAGNOSTIC_VALUE_FLAGS.contains(&arg.as_str()) => {
                    if let Some(value) = rustc_args.get(i + 1) {
                        parsed.diagnostic_flags.push(format!("{arg}={value}"));
                        i += 1;
                    } else {
                        parsed.diagnostic_flags.push(arg.clone());
                    }
                }
                _ if arg
                    .split_once('=')
                    .is_some_and(|(flag, _)| DIAGNOSTIC_VALUE_FLAGS.contains(&flag)) =>
                {
                    parsed.diagnostic_flags.push(arg.clone());
                }
'''+s[b:]
s=s.replace('    /// diagnostics / lint / query / already-keyed path flags that parsing','    /// modeled diagnostics / lint / query / path flags that parsing',1)
p.write_text(s)
p=worktree/'src/cache_key.rs';s=p.read_text()
a=s.index('    // Outcome-affecting lint configuration (-A/-W/-D/-F, their long forms,')
s=s[:a]+'''    // Always fold the version tag, including when no format was explicit:
    // older clients stored arbitrary diagnostic formats under that default key.
    hasher.set_group("diagnostics");
    fold_field(&mut hasher, b"diagnostics.v1:", b"");
    for flag in &args.diagnostic_flags {
        fold_field(&mut hasher, b"diagnostic_arg:", flag.as_bytes());
    }

'''+s[a:]
s=s.replace('    // key. Diagnostics / lint / query / already-keyed path flags are stripped','    // key. Modeled diagnostics / lint / query / path flags are stripped',1)
p.write_text(s)
