# Resume prompt

Paste the block below as your **first message** in a new chat. Nothing else is
needed ? it points the assistant at the handover file, which contains the full
state.

---
--- PASTE FROM HERE ---

I am continuing work on an existing project. Do not ask me to explain it.

Working directory: `C:\Users\Vinayak\Desktop\kiro`

Read these files first, in this order, before doing anything or proposing anything:

1. `AGENTS.md` ? binding rules and environment gotchas
2. `docs/HANDOVER.md` ? complete project state: what is built, what is pending,
   next steps, and bugs already fixed that must not be reintroduced
3. `docs/OPERATING_LAYER.md` ? ?4 lists exactly what is NOT built
4. `docs/WORK_REMAINING.md` ? prioritised remaining work

Then verify the state yourself rather than trusting the docs:

```powershell
$env:PYTHONPATH="C:\Users\Vinayak\Desktop\kiro\backend;C:\Users\Vinayak\Desktop\kiro"
cd C:\Users\Vinayak\Desktop\kiro\backend
..\.venv\Scripts\python.exe -m pytest -q
```

Expect 869 passed, fully offline. If the number differs, tell me before proceeding.

Three things about how I want you to work:

- **Run what you write.** Do not tell me code works without executing the tests.
  Add a regression test for every change.
- **Tell me when something is not built or not evidenced.** This project's main
  strength is that its documents distinguish measured results from specified
  design. Do not let a document, slide or UI imply otherwise.
- **The anchor invariant is not negotiable.** Anchors are computed from an
  append-only ledger and no agent can write one. If a task would require relaxing
  that, say so instead of working around it.

Once you have read those files, tell me in a few lines: the current test count you
measured, what you understand to be done, what is pending, and what you think the
next task should be. Then wait for me to confirm before writing code.

--- PASTE TO HERE ---
---

## Notes for you (not part of the paste)

**If the new chat has no file-write or shell access**, it will say the tool is "not
available to the current agent". That is an agent configuration problem, not a
permissions prompt. Fix it with:

```
/tools
```

to see what is loaded, and if `write` or `shell` are absent, restart with:

```
kiro-cli chat --trust-all-tools
```

If they are still absent, the agent's `tools` list does not include them ? check
`/agent` and switch to a default agent that does.

**If you want to work on a specific task**, append one line to the paste. For
example:

- `My task this session is the ablation harness ? WORK_REMAINING ?5.1.`
- `My task this session is the frontend ? use docs/FRONTEND_PROMPT.md.`
- `My task this session is knowledge evolution ? WORK_REMAINING ?5.2.`

**Keep the handover current.** Ask the assistant to update `docs/HANDOVER.md` at
the end of each session. If it drifts, the next chat starts from a false picture,
which is worse than starting from none.
