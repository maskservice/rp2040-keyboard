# Agent instructions

## Worktree placement and local working data

Use `wellmanifest/worktrees` v5 for any new linked delivery checkout:
`<primaryCheckout>/.worktrees/ticket-NNN--slug`, with branch `ticket/NNN-slug`
and an exact runtime lease in
`<primaryCheckout>/.subactor/leases/ticket-NNN--slug.json`.
Resolve the primary checkout through Git. Validate the layout and reject
symlinked path components before allocation. Git must support both
`worktree add --relative-paths` and `worktree repair --relative-paths`
(minimum 2.51.0); both administration pointers must be relative.

Preserve any explicit main-only workflow in this repository: no worktree is
required when working directly on main. Keep working data in ignored,
repository-local `.subactor/{sessions,recovery,receipts,cache,snapshots}/`.
Never use `/tmp` or a workspace-wide `.worktrees` for delivery work.
Keep `.subactor/manifest.json` tracked if present.

Legacy registrations are read-only recovery inventory. Before an exact
migration, audit dirty/ignored data, processes and IDEs, leases, pull requests
and HEAD reachability. Never automatically move, repair, delete or prune them.
See the shared policy and pinned read-only checker:
https://github.com/maskservice/.github/tree/main/worktrees
