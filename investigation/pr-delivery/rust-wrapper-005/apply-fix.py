from pathlib import Path
p = Path('src/compiler/rustdoc.rs')
s = p.read_text()
needle = 'fn scan_rust(bytes: &[u8]) -> Result<Vec<Found>> {\n    let tokens = rust_tokens(bytes);'
assert needle in s
s = s.replace(needle, needle + '\n    if has_environment_macro(&tokens) {\n        anyhow::bail!("rustdoc environment macros require compiler dependency tracking");\n    }', 1)
needle = 'fn is_include(name: &str) -> bool {'
assert needle in s
s = s.replace(needle, '''fn has_environment_macro(tokens: &[Tok]) -> bool {
    tokens.windows(3).any(|macro_tokens| {
        matches!(&macro_tokens[0], Tok::Ident(name) if matches!(name.as_str(), "env" | "option_env"))
            && punct_at(macro_tokens, 1, b'!')
            && matches!(macro_tokens[2], Tok::Punct(b'(' | b'[' | b'{'))
    })
}

''' + needle, 1)
p.write_text(s)
