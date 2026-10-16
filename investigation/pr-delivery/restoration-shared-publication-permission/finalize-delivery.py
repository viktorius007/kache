import json,pathlib,subprocess,sys
root=pathlib.Path(__file__).resolve().parent
worktree=pathlib.Path('/Users/viktor/Developer/github/kache-prs/restoration-shared-publication-permission')
def git(*args):return subprocess.check_output(['git',*args],cwd=worktree,text=True).strip()
assert sys.argv[1:]==['0'],'Only finalize after the full gate exits zero'
assert not git('status','--porcelain'),'Final source tip must be clean'
fix=git('rev-parse','HEAD');test=git('rev-parse','HEAD~1');base=git('rev-parse','HEAD~2')
assert base=='4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9'
files=git('diff','--name-only',base,'HEAD').splitlines()
gate='env CARGO_TARGET_DIR=/Users/viktor/Developer/github/kache-prs/restoration-literal-marker/target python3 /Users/viktor/Developer/github/kache-investigations/coordinator/investigation/pr-delivery/build-slot.py just check'
body='''In [`discard_staged_blob`](https://github.com/kunobi-ninja/kache/blob/4ee0f9e2b9673aa16f29c9c7e39bf8d0152671d9/crates/kache-store/src/store.rs#L4059-L4086), discarding a duplicate hardlinked snapshot cleared the existing blob’s read-only protection. Detect the shared winner, unlink its Unix staging alias without chmod, and restore the winner’s Windows protection after deletion. `duplicate_shared_publication_keeps_blob_readonly`, `losing_shared_publication_preserves_blob_readonly`, and the unshared-source control pass; `just check` passes.
'''
assert len(body.split())<=75
(root/'pr-body.md').write_text(body)
record=dict(id='restoration-shared-publication-permission',branch=git('branch','--show-current'),worktree=str(worktree),test_commit=test,fix_commit=fix,title='Keep published shared blobs read-only during duplicate publication',body_file=str(root/'pr-body.md'),base_sha=base,gate_command=gate,gate_exit=0,red_log=str(root/'logs/red.log'),green_log=str(root/'logs/green.log'),gate_log=str(root/'logs/gate.log'),changed_files=files)
(root/'delivery.json').write_text(json.dumps(record,indent=2)+'\n')
report=f'''STATUS: READY
COMMIT: {fix}
CHANGED: {len(files)} files
OPEN: 0
BLOCKERS: none
---

Test-only commit {test}; production fix commit {fix}; independent upstream baseline {base}. The owned source worktree is clean and contains no marker PR or other sibling changes. The exclusively owned private Cargo target was reused sequentially as authorized.

The public duplicate-put regression requires real device/inode sharing before checking readonly protection and preserved bytes. The existing publication seam tests both an already-present shared winner and one that appears during rename, requiring the staging alias to disappear and the winner to retain its readonly state. Baseline production failed all three shared states at behavioral permission assertions (logs/red.log and logs/race-red.log). The unshared-source control passed on baseline (logs/control-baseline.log), independently requiring the source to remain writable and a source rewrite to leave winning blob bytes unchanged. All new cases pass after repair, and the complete store suite passed (logs/green.log).

The repair extends existing discard_staged_blob with an optional winning blob path, reusing paths_share_inode. For a verified shared winner, Unix unlinks staging without changing the inode mode; Windows preserves existing readonly deletion semantics and re-arms that winner afterwards. Both losing-publication branches supply the winner; put validation cleanup supplies no winner and retains its prior behavior. Independent staging keeps its writable-source cleanup. No new helper, abstraction, visibility, test hook, process-global state, suppression or generic unlink behavior change was introduced. Shape checks found each edited function within default size limits; existing policy and identity knowledge are reused rather than duplicated.

The first full gate caught a needless borrow in the new public regression; only that borrow was corrected in the amended test-only commit (logs/gate-first.log). The production repair and oracle are unchanged. The required full gate `{gate}` exited 0 at final commit {fix} (logs/gate.log), including formatting, clippy, resource-guard checks and all workspace tests. The local runtime verification is macOS. The generic publication seam regressions are not platform-gated; Windows runtime verification remains for CI. CI owns mutation testing; no local cargo-mutants run was performed. Verification-notes.md records the oracle, discriminator fixtures, graph reuse searches and scope limits.

The saved original proof demonstrated the exported store API on a real generated HFS+ filesystem. The new Unix regression uses the already-existing thread-local ForceStoreHardlink only to choose the same no-CoW ingest path; real filesystem aliasing and publication remain intact. Ordinary Cargo recurrence and concurrent mutation exposure were not established and are not claimed by this PR. The original investigation source and evidence remain unchanged. Root independently reviews and publishes; this agent has not pushed the branch.
'''
(root/'report.md').write_text(report)
print('READY',root/'delivery.json')
