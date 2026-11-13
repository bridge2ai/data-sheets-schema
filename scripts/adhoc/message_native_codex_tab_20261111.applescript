-- Purpose: relay one line of authorized coordination from the Claude lead to
--   the native Codex helper's Terminal tab (the existing relay script covers
--   only the four agy tabs).
-- Inputs: one argument. Either the message (a single line pointing at a
--   written assignment file), or the literal word --submit.
--   Codex's input box takes the typed line as pasted text and does not submit
--   it (observed 2026-11-11T16:29Z), so delivery is two calls: the message,
--   then --submit, which sends one empty line (Enter) and only when the
--   lead's own pending text is visible in the input box.
-- Output: the verified TTY on delivery. Refuses, sending nothing, if the
--   window's TTY has changed, or (message) the tab does not show Codex's idle
--   input prompt, or (--submit) no pending "Claude lead" line is visible.
--   The text can therefore never land in a plain shell or a busy session.
-- Window id and TTY are those recorded in claude-lead-handoff-20261111.md.
-- Serves: owner decisions D130 to D132 (2026-11-11). No person is notified.
-- Date: 2026-11-11
on run argv
    if (count of argv) is not 1 then error "Expected one argument"
    set noteText to item 1 of argv
    if noteText contains linefeed or noteText contains return then error "Message must be one line"
    tell application "Terminal"
        with timeout of 10 seconds
            set workerTab to tab 1 of window id 339
            if tty of workerTab is not "/dev/ttys001" then error "Worker TTY changed"
            -- `contents of <variable>` dereferences the variable in AppleScript,
            -- so the tab is named in full here.
            set visibleText to (get contents of tab 1 of window id 339) as text
            if noteText is "--submit" then
                if visibleText does not contain "» Claude lead" then error "No pending lead message in the input box; nothing sent"
                do script "" in workerTab
                return "native submitted /dev/ttys001"
            end if
            if visibleText does not contain "Ask Codex to do anything" then error "Codex idle prompt not visible; nothing sent"
            do script noteText in workerTab
        end timeout
    end tell
    return "native delivered /dev/ttys001"
end run
