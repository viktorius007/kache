# Investigation archive

This archive preserves the complete histories and trees of 32 retired
investigation branches. Every original tip is a parent of this archive commit.
The archive tree contains only this guide and the branch-to-commit manifest;
research and prototype code have not been merged into the production branch.

List original branches and their exact commits in branches.json.
Inspect a snapshot without checking it out:

    git show <commit>:investigation/report.md
    git ls-tree -r --name-only <commit>

To recover an old branch when needed:

    git switch -c recovered-investigation <commit>

Fetch this archive into a fresh clone if it is not already present:

    git fetch origin tag archive/investigations-2026-10-30
