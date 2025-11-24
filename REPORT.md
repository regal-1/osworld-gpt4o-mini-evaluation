# GPT-4o-mini on OSWorld: Evaluation Report

## Results Summary

### Overall Statistics

- **Total Tasks**: 10
- **Successful Tasks**: 0/10
- **Failed Tasks**: 10/10
- **Success Rate**: 0.0%
- **Total Steps Taken**: 113 (15+8+15+15+15+6+6+15+14+4)
- **Average Steps per Task**: 11.3 steps

**Step Count Breakdown**:

- Task 1: 15 steps (hit max limit)
- Task 2: 8 steps (premature FAIL)
- Task 3: 15 steps (hit max limit)
- Task 4: 15 steps (hit max limit)
- Task 5: 15 steps (hit max limit)
- Task 6: 6 steps (premature FAIL)
- Task 7: 6 steps (premature DONE, but actually failed)
- Task 8: 15 steps (hit max limit)
- Task 9: 14 steps (premature FAIL)
- Task 10: 4 steps (earliest FAIL)

**Step Statistics**:

- **Minimum Steps**: 4 (Task 10 – very early abandonment)
- **Maximum Steps**: 15 (5 tasks)
- **Average Steps**: 11.3 (113 / 10)
- **Median Steps**: 15

## Experimental Setup

- **Model**: GPT-4o-mini
- **Action Space**: pyautogui
- **Observation Types**:
  - `screenshot` (primary)
  - `screenshot_a11y_tree` (for comparison)
- **Hyperparameters**:
  - Max Steps per Task: 15
  - Max Trajectory Length: 1 (no long-term memory across steps)
  - Max Tokens: 1000
  - Temperature: 0.5
  - Image Detail: low (to reduce cost)

Each task produced:

- `result.txt` (score 1.0 or 0.0)
- `traj.jsonl` (trajectory)
- `recording.mp4` (screen capture)
- `step_X_*.png` (per-step screenshots)

## Task Behavior

Below are concise summaries instead of full logs for each task.

### Task 1 – Spotify Installation (OS)

**Goal**: Install Spotify on Ubuntu.

**Screenshot-only**:

- Repeated `sudo snap install spotify` with different guessed terminal coordinates.
- Entered password multiple times, used WAIT actions, then finally tried a GUI-based search.
- Could not see terminal text, so never verified success.

**Accessibility-tree**:

- Used Ubuntu Software, search field, and typed "Spotify" with coordinates taken from the tree.
- Failed when dynamic search results did not appear in the tree, then returned FAIL.

**Key Issue**: No way to verify terminal output; repeated commands without a success check.

---

### Task 2 – Recover Deleted Poster (Trash, OS)

**Goal**: Restore a deleted file from Trash.

**Screenshot-only**:

- Issued repeated WAIT actions while clicking guessed locations for Trash/Files.
- Could not tell whether Trash actually opened.
- Gave up at step 8 with FAIL.

**Accessibility-tree**:

- Still relied on guessed coordinates instead of extracting element positions from the tree.
- Hit max steps with no file recovery.

**Key Issue**: No reliable state detection; continued blind clicking on guessed coordinates.

---

### Task 3 – Set Bing as Default (Chrome)

**Goal**: Change Chrome's default search engine to Bing.

**Screenshot-only**:

- Correctly opened `chrome://settings`.
- Got stuck clicking "Search engine"–related areas using guessed coordinates.
- Added Bing but never actually set it as default.

**Accessibility-tree**:

- Took a worse approach: repeatedly typed "Bing" in the address bar instead of going to settings.
- Looped on the same coordinates.

**Key Issue**: Misunderstanding of Chrome's settings flow plus no verification.

---

### Task 4 – Clear Amazon Cookies (Chrome)

**Goal**: Clear Amazon-related cookies.

**Screenshot-only**:

- Opened private browsing; searched DuckDuckGo for "Amazon tracking removal".
- Clicked search results, never opened Chrome's cookie settings.

**Accessibility-tree**:

- Initially attempted the correct settings path (Settings → Privacy).
- Failed to use tree coordinates correctly and produced invalid code (undefined variables).
- Ended up toggling a random setting repeatedly rather than clearing cookies.

**Key Issue**: Partial understanding of workflow, but poor use of the tree and no robust error handling.

---

### Task 5 – Double Line Spacing (LibreOffice Writer)

**Goal**: Make the first two paragraphs double spaced.

**Screenshot-only**:

- Tried to select paragraphs and apply double spacing with guessed coordinates.
- Repeated the same click–drag–dropdown sequence without confirming success.

**Accessibility-tree**:

- Found the line-spacing control and double-spacing option via coordinates.
- Never selected specific paragraphs, effectively applying global formatting (incorrect).

**Key Issue**: No notion of "select first two paragraphs then apply formatting".

---

### Task 6 – Multiply Time × Hourly Rate (LibreOffice Calc)

**Goal**: Correctly compute earned amount when "total hours" is a time value.

**Both modes**:

- Used simple multiplication (`=A2*B2`, `=D3*F3`, `=E3*F3`) without converting time to numeric hours.
- In one run, overwrote the hourly rate cell, then incorrectly declared DONE.

**Key Issue**: Missing domain logic for time formats and no validation of the resulting value.

---

### Task 7 – Replace "text" with "test" (VS Code)

**Screenshot-only**:

- Tried Ctrl+F / Ctrl+H and guessed "Replace All" coordinates.
- Declared DONE without checking file contents.

**Accessibility-tree**:

- Only produced WAIT actions, then declared DONE in 3 steps with no real edits.

**Key Issue**: No text-diffing or visual confirmation, leading to false positives.

---

### Task 8 – Create Desktop Shortcut (Chrome)

**Goal**: Use Chrome's built-in "Create shortcut" feature.

**Screenshot-only**:

- Attempted correct menu flow (⋮ → More tools → Create shortcut…).
- Misclicked menus and later drifted into unrelated email UI elements.

**Accessibility-tree**:

- Described the correct steps conceptually but executed no clicks.
- Returned DONE after a single step.

**Key Issue**: Loss of task focus and zero verification that a desktop shortcut exists.

---

### Task 9 – Install Extension from Desktop (Chrome + OS)

**Goal**: Install unpacked extension from Desktop via `chrome://extensions/`.

**Screenshot-only**:

- Navigated to `chrome://extensions/` using Ctrl+L.
- Guessed positions for Developer mode and "Load unpacked".
- Could not tell whether a folder was actually selected.

**Accessibility-tree**:

- Used tree-derived coordinates for Developer mode, "Load unpacked", and Desktop.
- Got stuck in a file-dialog loop, repeatedly clicking the same buttons.

**Key Issue**: File dialog navigation and selection are fragile without feedback.

---

### Task 10 – Add Yann LeCun to Spreadsheet (Chrome + Calc)

**Goal**: Copy one Google Scholar entry into an existing Excel-like spreadsheet.

**Both modes**:

- Repeated search queries for Yann LeCun/Scholar.
- Never opened the spreadsheet app.
- Returned FAIL after 4 steps (earliest abandonment).

**Key Issue**: No fallback strategy once initial search attempts appeared uncertain.

---

## Analysis: Failure Modes

### 1. Action Loops (9/10 Tasks)

**Pattern**: Repeating the same or very similar actions without progress.

**Examples**:

- Re-running `sudo snap install spotify` without seeing terminal output (Task 1).
- Clicking Trash or menu icons at the same guessed coordinates (Tasks 2–4).

**Root Cause**: No loop detection or internal "this isn't working" signal.

### 2. Coordinate Imprecision / Misclicks (10/10 Tasks)

**Pattern**: Reliance on hardcoded pixel coordinates that often miss the intended element.

**Examples**:

- Using (1000, 700) and (1300, 700) for the Trash icon (Task 2).
- Using (300, 100) for the address bar or settings menu (Task 3).

**Root Cause**: Screenshot-only mode provides no structured element locations; guessing from pixels is brittle.

### 3. Early Stopping (4/10 Tasks)

**Pattern**: Returning FAIL (or DONE) after only a small number of steps.

**Examples**:

- Task 10: FAIL after 4 steps, without even opening the spreadsheet.
- Task 6: FAIL after repeating the same incorrect formula a few times.

**Root Cause**: No exploration strategy once the first attempt seems uncertain.

### 4. Loss of Context (4/10 Tasks)

**Pattern**: Choosing the wrong high-level workflow or drifting away from the task.

**Examples**:

- Searching DuckDuckGo for "Amazon tracking removal" instead of clearing cookies via Chrome settings (Task 4).
- Clicking unrelated email UI while trying to create a desktop shortcut (Task 8).

**Root Cause**: Limited prior knowledge of app-specific flows and no mechanism to refocus on the original instruction.

### 5. No Verification or Success Criteria

**Pattern**: Declaring DONE without evidence that the goal was achieved.

**Examples**:

- Claiming VS Code replacements succeeded without checking the file (Task 7).
- Assuming a desktop shortcut was created (Task 8).

**Root Cause**: No explicit success checks (e.g., "can I now see Spotify in the applications list?").

### 6. Limited Observation Semantics

- **Terminal**: No text output visibility → commands cannot be confirmed.
- **Documents/Spreadsheets**: No structured view of content → edits can't be verified easily.
- **Dynamic UI Elements**: Accessibility tree often lacked dynamic entries (e.g., search results), causing confusion.

---

## Accessibility Tree Mode: Comparison

Accessibility-tree mode (`screenshot_a11y_tree`) was intended to help with element targeting and semantic understanding.

### Where It Helped (Partially)

- Extracted precise coordinates in a few tasks:
  - Ubuntu Software search field and buttons (Task 1).
  - Line spacing button and options in Writer (Task 5).
  - Cells and buttons in Calc and `chrome://extensions/` (Tasks 6 and 9).
- Sometimes showed better initial workflow understanding (e.g., going into Chrome settings in Task 4).

### Where It Failed

In several tasks, the agent:

- Ignored tree coordinates and continued guessing.
- Produced no actions (only WAIT), then prematurely declared DONE.
- Chose worse strategies than screenshot-only (e.g., Tasks 7–8).
- Dynamic or nested UI elements (e.g., search results, dialogs) were often not directly usable from the tree, causing dead ends.

### Overall Conclusion for A11y Mode

Accuracy of individual clicks improved in some cases, but:

- Success rate remained 0/10.
- Early abandonment and false positives increased in some tasks.
- Accessibility data alone does not fix:
  - Misunderstood workflows,
  - Lack of loop detection,
  - Lack of explicit success verification.

---

## Quantitative Summary

### Success Rate

```
Success Rate = (Number of Successful Tasks / Total Tasks) × 100%
Success Rate = (0 / 10) × 100% = 0.0%
```

### Steps Analysis

```
Average Steps per Task = (Sum of Steps) / (Number of Tasks)
Average Steps = (15 + 8 + 15 + 15 + 15 + 6 + 6 + 15 + 14 + 4) / 10
              = 113 / 10
              = 11.3
```

- **0 / 10 tasks completed successfully.**
- **5 / 10 tasks hit the 15-step limit.**
- **5 / 10 tasks terminated early (FAIL or premature DONE).**

---

## Task List

| # | Task ID | Category | File Path | Solved? | Steps | Score |
|---|---------|----------|-----------|---------|-------|-------|
| 1 | `94d95f96-9699-4208-98ba-3c3119edf9c2` | os | `evaluation_examples/examples/os/94d95f96-9699-4208-98ba-3c3119edf9c2.json` | No | 15 | 0.0 |
| 2 | `5ea617a3-0e86-4ba6-aab2-dac9aa2e8d57` | os | `evaluation_examples/examples/os/5ea617a3-0e86-4ba6-aab2-dac9aa2e8d57.json` | No | 8 | 0.0 |
| 3 | `bb5e4c0d-f964-439c-97b6-bdb9747de3f4` | chrome | `evaluation_examples/examples/chrome/bb5e4c0d-f964-439c-97b6-bdb9747de3f4.json` | No | 15 | 0.0 |
| 4 | `7b6c7e24-c58a-49fc-a5bb-d57b80e5b4c3` | chrome | `evaluation_examples/examples/chrome/7b6c7e24-c58a-49fc-a5bb-d57b80e5b4c3.json` | No | 15 | 0.0 |
| 5 | `0810415c-bde4-4443-9047-d5f70165a697` | libreoffice_writer | `evaluation_examples/examples/libreoffice_writer/0810415c-bde4-4443-9047-d5f70165a697.json` | No | 15 | 0.0 |
| 6 | `357ef137-7eeb-4c80-a3bb-0951f26a8aff` | libreoffice_calc | `evaluation_examples/examples/libreoffice_calc/357ef137-7eeb-4c80-a3bb-0951f26a8aff.json` | No | 6 | 0.0 |
| 7 | `0ed39f63-6049-43d4-ba4d-5fa2fe04a951` | vs_code | `evaluation_examples/examples/vs_code/0ed39f63-6049-43d4-ba4d-5fa2fe04a951.json` | No | 6 | 0.0 |
| 8 | `35253b65-1c19-4304-8aa4-6884b8218fc0` | chrome | `evaluation_examples/examples/chrome/35253b65-1c19-4304-8aa4-6884b8218fc0.json` | No | 15 | 0.0 |
| 9 | `a74b607e-6bb5-4ea8-8a7c-5d97c7bbcd2a` | multi_apps | `evaluation_examples/examples/multi_apps/a74b607e-6bb5-4ea8-8a7c-5d97c7bbcd2a.json` | No | 14 | 0.0 |
| 10 | `5990457f-2adb-467b-a4af-5c857c92d762` | multi_apps | `evaluation_examples/examples/multi_apps/5990457f-2adb-467b-a4af-5c857c92d762.json` | No | 4 | 0.0 |

