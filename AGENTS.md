When a one-off task needs a Python package that is not already available, write a temporary PEP 723 script with a `# /// script` dependency block and run it with `uv run` so dependencies are installed in an ephemeral environment. Remove the temporary script after use.

# Rebasing

When Anders asks to rebase a branch on another, first check if the current branch's changes can be cleanly replayed on top of the rebase target and do that preferentially. When rebasing, if there are any conflicts, DON'T try and fix them, surface them to Anders so you can discuss with him how best to handle them.

# Writing Tests

When implementing tests, always launch an adversarial review agent when the tests are done to check whether the tests actually test anything useful or are just encoding the current code behaviour, whether there are holes in the tested coverage, and whether tests are making invalid assumptions about the intended behaviour or environment.

# Reviewing Code

When Anders asks to launch one or more reviewers, make them adversarial, and collate their findings into a single report to discuss with Anders. Don't ever start fixing things without discussing with Anders first.

# ASWF Pixi Packaging

This repository is a new version of `~/code/pixi-recipes`. It builds conda packages with `rattler-build` and provides `pixi.toml` files for easy consumption of those packages.

Core goals:

- Upload built packages to `anaconda.org`.
- The `anaconda.org` channel/user is `anderslanglands`; the consumer channel URL is `https://conda.anaconda.org/anderslanglands`.
- Support both local test uploads and build/upload from GitHub Actions.
- Store individual version recipes in this repo, for example `imath/3.1.2` and `imath/3.2.2`, so changes and fixes remain trackable over time. Start with one version per package unless Anders asks for more.
- Use a single `recipe.yaml` per package version for all build flavours.
- Represent different feature combinations as separate `outputs` from that one recipe, including shared build/staging outputs where useful.
- Confirm the actual `anaconda.org` organization/channel with Anders before hard-coding upload targets, consumer channels, or GitHub Actions upload destinations.
- Expose different subpackages as pixi features.
- Name runtime library subpackages with a `-lib` suffix and development subpackages with a `-dev` suffix, for example `imath-lib` and `imath-dev`, not `-devel`.
- Prefer keeping the upstream/default package name, for example `imath`, as a compatibility metapackage that depends on the useful default split packages.
- Do not use local dependency paths in `pixi.toml`; that approach was not worth it.

Package conversion process:

- Work through packages from `~/code/pixi-recipes` one by one.
- For each package, do not immediately implement the conversion. First inspect the old recipe and propose a package breakdown for discussion with Anders.
- Discuss which subpackages should exist, which outputs should be published, and which pixi features should expose them.
- Prefer avoiding upstream patches. If builds fail, surface the problem to Anders with options and a recommendation before patching upstream library code.
- Keep this `AGENTS.md` updated as the process evolves.
- Keep root build tooling solvable before packages are uploaded; put package-specific consumer pixi feature manifests next to the versioned recipe when publishing has not happened yet.
