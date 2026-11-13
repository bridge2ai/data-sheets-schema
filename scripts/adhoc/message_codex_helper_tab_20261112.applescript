-- Purpose: relay one line of authorized coordination from the Claude lead to
--   one Codex helper's Terminal tab, chosen by window id and TTY. After the
--   restart of 2026-11-12 there are three Codex helper tabs with new window
--   ids, and the earlier relay (message_native_codex_tab_long_timeout_20261112)
--   names one fixed window.
-- Inputs: three arguments: the Terminal window id, the tab's TTY (for example
--   /dev/ttys045), and either the message (one line pointing at a written
--   assignment file) or the literal word --submit.
--   Codex's input box takes a typed line as pasted text and does not submit
--   it, so delivery is two calls: the message, then --submit, which sends one
--   empty line (Enter) only when a pending "Claude lead" line is visible.
-- Output: the verified TTY on delivery. Refuses, sending nothing, when the
--   window's TTY differs from the one given, when the tab does not show
--   Codex's input prompt, when Codex is working ("esc to interrupt" visible),
--   or (--submit) when no pending lead line is visible. The text can therefore
--   never land in a plain shell, in another program or in a busy session.
-- Serves: owner direction D134 and the owner's instruction of 2026-11-12 to
--   delegate to three Codex helper sessions. No person is notified.
-- Date: 2026-11-12
on run argv
    if (count of argv) is not 3 then error "Expected window id, tty and message"
    set windowId to (item 1 of argv) as integer
    set wantedTty to item 2 of argv
    set noteText to item 3 of argv
    if noteText contains linefeed or noteText contains return then error "Message must be one line"
    tell application "Terminal"
        with timeout of 90 seconds
            set workerTab to tab 1 of window id windowId
            if tty of workerTab is not wantedTty then error "Worker TTY changed"
            set visibleText to (get contents of tab 1 of window id windowId) as text
            -- The placeholder "Ask Codex to do anything" and the "for shortcuts"
            -- hint both disappear once text is pending (seen 2026-11-12), so
            -- the submit step is recognised by the pending lead line itself.
            if visibleText contains "esc to interrupt" then error "Codex is working; nothing sent"
            if noteText is "--submit" then
                if visibleText does not contain "Claude lead:" then error "No pending lead message visible; nothing sent"
                do script "" in workerTab
                return "submitted " & wantedTty
            end if
            if visibleText does not contain "Ask Codex to do anything" then error "Codex input prompt not empty or not visible; nothing sent"
            do script noteText in workerTab
        end timeout
    end tell
    return "delivered " & wantedTty
end run
