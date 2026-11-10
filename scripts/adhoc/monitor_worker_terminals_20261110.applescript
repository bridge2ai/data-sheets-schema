-- Purpose: read bounded live viewports of the five owner-designated D4D workers.
-- Inputs: existing Terminal window IDs, verified by the lead on 2026-11-10.
-- Output: labeled terminal viewports to stdout; no writes or keystrokes.
-- A scrolled viewport can be stale; corroborate handoffs with saved report/STATUS.
-- Full-history AppleEvents stalled under memory/disk pressure on this host.
-- Serves: active lead monitoring and the PR 5711 coordination evidence record.
-- Date: 2026-11-10. Run with osascript from the lead session.
tell application "Terminal"
    set reportText to ""
    repeat with workerWindow in {3155, 6245, 341, 6921, 339}
        try
            with timeout of 3 seconds
            set workerTab to tab 1 of window id workerWindow
            set recentHistory to (get contents of tab 1 of window id workerWindow) as text
            if length of recentHistory > 1500 then
                set recentHistory to text -1500 thru -1 of recentHistory
            end if
            set reportText to reportText & "WINDOW " & workerWindow & " TTY " & tty of workerTab & " VIEWPORT" & linefeed & recentHistory & linefeed
            end timeout
        on error errorText
            set reportText to reportText & "WINDOW " & workerWindow & " unavailable: " & errorText & linefeed
        end try
    end repeat
    return reportText
end tell
