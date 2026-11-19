# Pushing this fork to GitHub (`jake-net`)

This repository was assembled locally from the upstream clone plus the installed
customisations, and verified as a self-contained repo (`git bundle` produced).
It has **not** been pushed anywhere: this add-on's shell has `git` and network
access but **no GitHub CLI and no credentials**, and the agent does not handle
credentials. Push it from a machine where you are authenticated.

## What you have

- Branch `jake-net-mods` = upstream `v0.2.1` + the customisations + docs.
- Tags: `jake-net-v0.2.1-mods`, `jake-net-v0.2.1-mods-docs`.
- Full upstream history and tags (so future merges with upstream work normally).
- `growatt-local-jake-net.bundle` — the whole repo in one file, for transfer.

## Option A — a true GitHub fork (recommended)

1. On GitHub, fork `WouterTuinstra/Homeassistant-Growatt-Local-Modbus` into the
   `jake-net` account. Call it e.g. `homeassistant-growatt-local-modbus`.
2. On your machine:
   ```
   git clone https://github.com/jake-net/homeassistant-growatt-local-modbus.git
   cd homeassistant-growatt-local-modbus
   git fetch /path/to/growatt-local-jake-net.bundle jake-net-mods:jake-net-mods
   git checkout jake-net-mods
   git push -u origin jake-net-mods
   git push origin jake-net-v0.2.1-mods jake-net-v0.2.1-mods-docs
   ```

## Option B — a standalone repo (no upstream fork relationship)

1. Create an empty repo under `jake-net` (e.g. `growatt-local-modbus`), no README.
2. ```
   git clone /path/to/growatt-local-jake-net.bundle growatt-local-modbus
   cd growatt-local-modbus
   git remote set-url origin https://github.com/jake-net/<repo>.git
   git push -u origin jake-net-mods
   git push origin --tags
   ```
   (This also pushes upstream's tags, which keeps the merge base intact.)

## Option C — from a bundle only

```
git clone --bare growatt-local-jake-net.bundle growatt.git
cd growatt.git
git push --mirror https://github.com/jake-net/<repo>.git
```

## After pushing

- Keep `upstream` as a remote so the merge in `MERGE-NOTES-v0.3.1.md` can be
  done directly:
  ```
  git remote add upstream https://github.com/WouterTuinstra/Homeassistant-Growatt-Local-Modbus.git
  git fetch upstream --tags
  git checkout -b merge-v0.3.1 upstream/v0.3.1
  ```
- Do **not** push to `master` on the fork; keep `jake-net-mods` as the working
  branch and open PRs from it when eventually contributing back upstream.
