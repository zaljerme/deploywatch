# GitHub handoff

The public `zaljerme/deploywatch` repository was not accessible during implementation.
Nothing was pushed, and no GitHub issue or PR was created. Local branches are ready:

- `main`: minimal project initialization.
- `milestone-1-monitoring`: monitoring engine, API, migrations, tests, and local demo.
- `milestone-2-dashboard`: builds on milestone one with dashboard, GitHub activity, and documentation.

## Create the repository and push

On GitHub, use **+ → New repository**, owner **zaljerme**, name **deploywatch**.
Do not initialize a README, license, or .gitignore because this local repository already has commits.
If the repository exists but is private, use your normal authenticated Git access and inspect its
history before pushing. Do not force-push over an existing project.

From this local repository root:

```powershell
git remote add origin https://github.com/zaljerme/deploywatch.git
git push -u origin main
git push -u origin milestone-1-monitoring
git push -u origin milestone-2-dashboard
```

If `origin` already exists, inspect `git remote -v` and skip the add command when it is correct.
Git Credential Manager may prompt you to sign in. Never put a personal access token in the URL.

## PR 1

Open **Pull requests → New pull request**. Select base **main**, compare
**milestone-1-monitoring**. Review **Files changed**, then **Create pull request**.

Title: **Implement persistent monitoring and incident detection**

Description:

```text
Add a FastAPI monitor-management API and a separate PostgreSQL-backed worker. Checks record
HTTP status, latency, and network failure categories. Three consecutive failures open one
incident; the next successful check resolves it.

Use row locks and a partial unique index to prevent overlapping checks and duplicate open
incidents. Add Alembic migrations, bearer authentication, DNS-pinned SSRF restrictions, a
development-only controllable target, and Docker Compose configuration.

Validation: local API/state-machine and HTTP safety tests passed, including a PostgreSQL
two-worker contention test. PostgreSQL migrations passed upgrade/downgrade/re-upgrade and
schema-drift checks. Docker was unavailable locally; verify the Compose demo before merging.
```

Check **Actions** for the backend job, read its test output, and run the README demo with Docker.
Return to the PR's **Conversation** tab. When checks and your review pass, choose **Create a merge
commit → Confirm merge**. Leave this merge for yourself; it has not been performed automatically.
Keep the milestone-one branch until PR 2 has merged.

## PR 2

After PR 1 is merged, open a new PR with base **main**, compare **milestone-2-dashboard**.
Using a merge commit for PR 1 preserves ancestry, so PR 2 shows only the second milestone.
If you squash PR 1 instead, rebase the second milestone onto the updated main branch before
opening PR 2; do not blindly force-push.

Title: **Add monitoring dashboard and GitHub investigation context**

Description:

```text
Add a responsive React/TypeScript dashboard with monitor controls, recent checks, response-time
charts, sampled uptime, and incident timelines. Show empty, loading, stale, and error states.

Fetch GitHub commits and deployment records independently, with bounded pagination, deadlines,
response sizes, caching, and rate-limit cooldowns. Label activity as investigation clues and
deployment completion as unverified. GitHub failures do not alter monitoring state.

Document setup, the outage/recovery demo, security boundaries, architecture, limits, verification,
and interview talking points. Extend GitHub Actions with frontend tests and a TypeScript build.

Validation: 33 backend tests and four frontend tests passed locally; Ruff, TypeScript, and Vite
build passed. A live worker/demo run opened one incident after three failures and resolved it on
recovery. Hosted CI and the Compose/Nginx stack still need verification before merge.
```

Review the changed files and both Actions jobs. Run `docker compose up --build -d`, open
http://localhost:8080, create the demo monitor, and demonstrate outage and recovery. Enter a
repository and verify commits and deployment records have different labels. Then use
**Create a merge commit → Confirm merge** after checks pass. Branch deletion is optional afterward.

## Achievement status and evidence

As reported by you: YOLO is confirmed earned; Quickdraw was attempted but is unconfirmed;
Pull Shark is unconfirmed. The public profile did not expose enough detail to change that status.
Check your signed-in profile's **Achievements** section and open each badge's detail view.

GitHub's public UI evidence and community reports describe Pull Shark's first tier as two authored
PRs merged, and Quickdraw as closing an issue or PR within five minutes of opening. The evidence
is documented in [GitHub UI fragment research](https://conroy1988.github.io/Achievements/official-achievement-fragments/)
and [this GitHub Community discussion](https://github.com/orgs/community/discussions/34848).
These are reported criteria, not a guaranteed or stable API contract. Badge indexing can be
delayed, and qualifying work does not guarantee immediate display. Your earlier YOLO PR may
already count toward Pull Shark if it was authored by you and merged.

The two useful milestone PRs provide an honest contribution trail. Search your PR history with
`is:pr is:merged author:zaljerme` and confirm authorship/base branches. Never add coauthors who
did not contribute, manufacture collaboration, or create meaningless issues for a badge.

## Optional small task if Quickdraw is still missing

A real setup limitation is that the repository has PowerShell demo commands but no portable Bash
demo walkthrough. If you use Bash/WSL, adding and testing that walkthrough is a useful task.
Prepare and verify equivalent `curl` commands first; do not call them tested before running them.

Once the documentation is ready, open an issue titled **Document the demo commands for Bash**.
Describe the PowerShell-only gap and the healthy → failing → recovered acceptance check. Commit
the tested documentation on `docs/bash-demo`, push it, and open a documentation PR. Close the
issue as completed after the fix is actually available, linking the commit or PR and stating
whether the PR is merged or still proposed. If this happens within five minutes of issue creation,
it may meet the reported Quickdraw criterion. Do not rush review or claim a proposed fix is merged.

This optional task has not been performed or staged. If you do not use Bash, wait for a genuine
small problem you encounter rather than inventing a task just to obtain the badge.
