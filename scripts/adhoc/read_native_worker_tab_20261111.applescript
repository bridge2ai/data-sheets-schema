-- Purpose: read one assigned D4D worker tab when the fleet monitor times out.
-- Inputs: role; output: verified TTY and visible terminal contents.
-- Serves native efficiency review issues 5842/5847, 2026-11-11. Read-only.
on run argv
    if count of argv is not 1 then error "Expected worker role"
    set roleName to item 1 of argv
    set targets to {{"agy3", 341, "/dev/ttys002"}, {"agy4", 6921, "/dev/ttys010"}}
    repeat with targetSpec in targets
        if item 1 of targetSpec is roleName then
            with timeout of 30 seconds
                tell application "Terminal"
                    set workerTab to tab 1 of window id (item 2 of targetSpec)
                    if tty of workerTab is not (item 3 of targetSpec) then error "Worker TTY changed"
                    set viewportText to (get contents of tab 1 of window id (item 2 of targetSpec)) as text
                    if length of viewportText > 3500 then set viewportText to text -3500 thru -1 of viewportText
                    return (tty of workerTab) & linefeed & viewportText
                end tell
            end timeout
        end if
    end repeat
    error "Unknown worker role"
end run
