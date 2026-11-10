-- Purpose: dispatch the human-authorized bounded readiness briefs to four verified D4D workers.
-- Inputs: verified Terminal window/TTY identities and durable assignment files.
-- Output: labeled delivery acknowledgments; no shell commands or person notifications.
-- Serves: final-generation readiness plan, 2026-11-10.
set assignments to {{3155, "/dev/ttys034", "agy1"}, {6245, "/dev/ttys048", "agy2"}, {341, "/dev/ttys002", "agy3"}, {6921, "/dev/ttys010", "agy4"}}
set briefRoot to "/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-final-generation-readiness-20261110/notes/final_generation_readiness_20261110/"
set resultText to ""
tell application "Terminal"
    repeat with spec in assignments
        set windowNumber to item 1 of spec
        set expectedTTY to item 2 of spec
        set roleName to item 3 of spec
        with timeout of 5 seconds
            set workerTab to tab 1 of window id windowNumber
            if tty of workerTab is not expectedTTY then error "Worker TTY changed; assignment refused"
            set instructionText to "Lead assignment under the human's new implementation authorization. Read " & briefRoot & "PLAN.md and " & briefRoot & "assignments/" & roleName & ".md, then execute that bounded assignment. Earlier standby is superseded only for this task. G1 owns initial runtime budget; all others prepare/read/edit only until lead grants execution. Report to the assigned handoff file. Acknowledge and start now."
            do script instructionText in workerTab
            set resultText to resultText & roleName & " delivered to window " & windowNumber & " " & expectedTTY & linefeed
        end timeout
    end repeat
end tell
return resultText
