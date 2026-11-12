-- Purpose: deliver already-queued lead guidance through the worker TUI's Alt-M shortcut.
-- Inputs: one designated role with a verified TTY and visible queued-message prompt.
-- Output: acknowledgment; no shell command, process termination or person notification.
-- Serves final-generation readiness coordination, 2026-11-10.
on run argv
    if count of argv is not 1 then error "Expected one worker role"
    set roleName to item 1 of argv
    set targets to {{"agy1", 3155, "/dev/ttys034"}, {"agy2", 6245, "/dev/ttys048"}, {"agy3", 341, "/dev/ttys002"}, {"agy4", 6921, "/dev/ttys010"}}
    repeat with targetSpec in targets
        if item 1 of targetSpec is roleName then
            tell application "Terminal"
                with timeout of 5 seconds
                    set workerTab to tab 1 of window id (item 2 of targetSpec)
                    if tty of workerTab is not (item 3 of targetSpec) then error "Worker TTY changed"
                    set viewport to (get contents of tab 1 of window id (item 2 of targetSpec)) as text
                    if viewport does not contain "alt+m to send immediately" then error "No queued-message shortcut visible; no key sent"
                    do script ((ASCII character 27) & "m") in workerTab
                end timeout
            end tell
            return roleName & " queued-guidance shortcut delivered"
        end if
    end repeat
    error "Unknown worker role"
end run
