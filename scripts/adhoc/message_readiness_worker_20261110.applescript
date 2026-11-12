-- Purpose: relay authorized coordination to one verified D4D coding worker.
-- Inputs: role and message arguments; output: verified delivery role/TTY.
-- Serves final-generation readiness, 2026-11-10; no shell execution or person notification.
on run argv
    if count of argv is not 2 then error "Expected role and message"
    set roleName to item 1 of argv
    set noteText to item 2 of argv
    set targets to {{"agy1", 3155, "/dev/ttys034"}, {"agy2", 6245, "/dev/ttys048"}, {"agy3", 341, "/dev/ttys002"}, {"agy4", 6921, "/dev/ttys010"}}
    repeat with targetSpec in targets
        if item 1 of targetSpec is roleName then
            tell application "Terminal"
                with timeout of 5 seconds
                    set workerTab to tab 1 of window id (item 2 of targetSpec)
                    if tty of workerTab is not (item 3 of targetSpec) then error "Worker TTY changed"
                    do script noteText in workerTab
                end timeout
            end tell
            return roleName & " delivered " & (item 3 of targetSpec)
        end if
    end repeat
    error "Unknown worker role"
end run
