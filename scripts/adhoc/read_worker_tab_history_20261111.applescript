-- Purpose: read the tail of one D4D worker tab's scrollback, so a report a
--   worker printed but did not save to disk can be collected by the lead.
-- Inputs: role (agy1|agy2|agy3|agy4|native), optional character bound
--   (default 12000, capped at 60000).
-- Output: verified TTY, then the last N characters of the tab's history.
--   Read-only: no keystrokes, no writes. Refuses if the TTY has changed.
-- Window ids and TTYs are those recorded in claude-lead-handoff-20261111.md.
-- Full-history AppleEvents stalled under memory pressure on 2026-11-10; this
--   reads one tab per call under a 45 s timeout rather than the whole fleet.
-- Serves: lead transfer 2026-11-11 (PR 5858 report branch). Date: 2026-11-11.
on run argv
    if (count of argv) < 1 then error "Expected worker role"
    set roleName to item 1 of argv
    set charBound to 12000
    if (count of argv) > 1 then set charBound to (item 2 of argv) as integer
    if charBound > 60000 then set charBound to 60000
    set targets to {{"agy1", 3155, "/dev/ttys034"}, {"agy2", 6245, "/dev/ttys048"}, {"agy3", 341, "/dev/ttys002"}, {"agy4", 6921, "/dev/ttys010"}, {"native", 339, "/dev/ttys001"}}
    repeat with targetSpec in targets
        if item 1 of targetSpec is roleName then
            with timeout of 45 seconds
                tell application "Terminal"
                    set workerTab to tab 1 of window id (item 2 of targetSpec)
                    if tty of workerTab is not (item 3 of targetSpec) then error "Worker TTY changed"
                    set historyText to (get history of workerTab) as text
                    if length of historyText > charBound then set historyText to text -charBound thru -1 of historyText
                    return (tty of workerTab) & linefeed & historyText
                end tell
            end timeout
        end if
    end repeat
    error "Unknown worker role"
end run
