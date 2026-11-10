-- Purpose: read bounded live histories of the five owner-designated D4D workers.
-- Inputs: existing Terminal window IDs, verified by the lead on 2026-11-10.
-- Output: labeled recent terminal histories to stdout; no writes or keystrokes.
-- Serves: active lead monitoring and the PR 5711 coordination evidence record.
-- Date: 2026-11-10. Run with osascript from the lead session.
tell application "Terminal"
    set reportText to ""
    repeat with workerWindow in {3155, 6245, 341, 6921, 339}
        try
            set workerTab to tab 1 of window id workerWindow
            set recentHistory to history of workerTab
            if length of recentHistory > 1500 then
                set recentHistory to text -1500 thru -1 of recentHistory
            end if
            set reportText to reportText & "WINDOW " & workerWindow & " TTY " & tty of workerTab & linefeed & recentHistory & linefeed
        on error errorText
            set reportText to reportText & "WINDOW " & workerWindow & " unavailable: " & errorText & linefeed
        end try
    end repeat
    return reportText
end tell
