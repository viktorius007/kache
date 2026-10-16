#[path = "../src/policy.rs"]
mod policy;
fn main() {
    for (event, ref_type, protected, expected) in [
        ("pull_request", "branch", "false", true),
        ("pull_request_target", "branch", "true", true),
        ("workflow_run", "branch", "true", true),
        ("release", "tag", "true", true),
        ("push", "branch", "true", false),
        ("push", "branch", "false", true),
    ] {
        let get = |name: &str| match name {
            "GITHUB_ACTIONS" => Some("true".to_string()),
            "GITHUB_EVENT_NAME" => Some(event.to_string()),
            "GITHUB_REF_TYPE" => Some(ref_type.to_string()),
            "GITHUB_REF_PROTECTED" => Some(protected.to_string()),
            _ => None,
        };
        let actual = policy::forced_remote_readonly_with(get).is_some();
        println!("event={event} ref_type={ref_type} protected={protected}: readonly={actual}");
        assert_eq!(actual, expected);
    }
}
