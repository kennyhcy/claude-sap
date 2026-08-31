# SAP Note fetcher - uses headless Edge with a dedicated profile to reuse the
# SAP login session, then saves the note API JSON to a local file.
#
# WHY HEADLESS EDGE (not Invoke-WebRequest):
#   SAP's session cookie is HttpOnly, so neither the wininet API nor
#   document.cookie can read it. A browser process, however, sends HttpOnly
#   cookies itself when it visits a URL. So we let Edge (pointed at a dedicated
#   user-data-dir that already holds the logged-in session) visit the SAP Note
#   API and capture the response, which we save to disk.
#
# USAGE:
#   powershell -ExecutionPolicy Bypass -File get_sapnote.ps1 <noteNumber>
#   powershell -ExecutionPolicy Bypass -File get_sapnote.ps1 3021593
#
# The note number is passed as the only positional argument. It is zero-padded
# to 10 digits if purely numeric, then the script:
#   1) Tries a headless Edge fetch against
#        https://me.sap.com/backend/raw/sapnotes/Detail?q=<note>&isVTEnabled=false
#      using --dump-dom. The DOM is captured; the raw JSON body is extracted
#      from the first <pre> element (Edge wraps JSON responses in <pre>...</pre>)
#      and HTML entities are decoded back to their original characters. The
#      result is saved to <note>.json under the sap-notes/ subfolder next to
#      this script (the cache dir; created on startup if missing).
#   2) If the profile is in use by a leftover Edge window, it is closed and the
#      headless fetch is retried once.
#   3) If the response looks like a login redirect (session expired), the
#      script opens a NORMAL (windowed) Edge using the dedicated profile dir
#      and lands on https://me.sap.com. The user logs in to SAP there. While
#      the login window is open the script does NOTHING that touches the
#      profile (an earlier version ran a headless session probe every few
#      seconds against the same profile dir, but Chromium does not allow two
#      processes to share a profile, so that probe kept stealing the profile
#      lock and froze the foreground login window). Instead the script only
#      counts profile Edge processes via WMI and waits for the user to CLOSE
#      the Edge window THEMSELVES. A user-initiated close after a confirmed
#      login gives Edge a clean, full shutdown that reliably flushes the
#      HttpOnly session cookie to the profile's cookie store. Once all profile
#      Edge processes are gone, the script fetches the note directly; session
#      validity is judged solely by Try-FetchNote's return (it retries 3x and
#      validates the JSON response). No terminal interaction is required
#      beyond closing the window - the user just logs in, confirms success,
#      and closes the window. Waits for up to 10 minutes before timing out.
#
# No args: prints usage.
#
# IMPLEMENTATION CHOICE (--dump-dom + <pre> extraction):
#   --dump-dom makes headless Edge render the URL and print the resulting DOM
#   to stdout. Because it is the browser itself making the request, it sends
#   the profile's HttpOnly cookies automatically - this is exactly what we need
#   and what the previous wininet approach could never do.
#
#   For an application/json URL, Edge (Chromium) renders the raw JSON text
#   inside a single <pre> element, e.g.:
#       <html><head>...<meta charset="utf-8"></head><body><pre>{ ...json... }
#       </pre><div class="json-formatter-container"></div></body></html>
#   So we extract the text between the first <pre ...> and its </pre>, decode
#   the HTML entities that dump-dom adds (&lt; &gt; &quot; &#39; &amp;), and
#   write that raw text straight to the .json file WITHOUT re-serializing it
#   (ConvertTo-Json would reorder/reformat/lossy-convert the original content).
#   The <pre>-wrapping behavior is stable Chromium behavior and has not changed
#   in years. As a guard, the fetcher validates that the extracted body is valid
#   JSON before accepting it - if Edge ever stops wrapping JSON in <pre>, or the
#   session is invalid and Edge serves an HTML login/shell page instead, the
#   body fails JSON validation and is treated as a login failure (no .html
#   fallback is written, so no garbage file is ever silently saved).
#
#   stdout is redirected straight to a temp file via Start-Process
#   -RedirectStandardOutput, then read as UTF-8, to dodge PowerShell's stdout
#   encoding pitfalls (UTF-8 bytes decoded as the console code page -> mojibake).
#
#   ALTERNATIVE NOT USED (documented for the record):
#   --remote-debugging-port + Chrome DevTools Protocol (Network.getResponseBody)
#   would fetch the raw HTTP response body directly, with no DOM wrapping or
#   entity escaping at all. It is the cleanest option, but requires a WebSocket /
#   HTTP-CDP client and careful process-lifecycle handling (broker/child procs),
#   which adds many failure points. The --dump-dom approach above is far simpler
#   and returns byte-faithful JSON after entity decoding, so it is preferred.
#
# KNOWN LIMITS:
#   - On first ever use (or if the profile dir does not exist), the script
#     skips the headless attempt and goes straight to opening the login window.
#   - When the session expires, the script opens a windowed Edge for login and
#     waits for the user to close it, then re-fetches automatically.
#   - --dump-dom waits for the load event; for a plain JSON endpoint this is
#     fast and reliable.
#   - If Edge is already running with the SAME user-data-dir, a new instance
#     may hand off to the existing one and --dump-dom will not execute. We
#     therefore use a profile dir that is NOT your everyday Edge profile.
#   - ASCII-only script text (no Chinese) to avoid PowerShell UTF-8 parsing
#     issues on Windows.
#   - Output files are for LOCAL viewing only. Do not redistribute.

param(
    # ValueFromRemainingArguments captures EVERY positional arg, so the script
    # accepts one OR many note numbers in a single call. Fetching many notes is
    # done SERIALLY inside one process - never by launching parallel processes,
    # because they would share one Edge profile dir and Chromium forbids two
    # processes using it concurrently (that is exactly the bug that used to get
    # one instance's login window force-killed by another).
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [string[]]$NoteNumbers = @()
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Cache dir: every fetched note JSON lives under this subfolder, so already-read
# notes can be reused next time without hitting the network. Created on startup
# if missing (also covers first-ever run).
$CacheDir = Join-Path $scriptDir "sap-notes"
if (-not (Test-Path $CacheDir)) {
    New-Item -ItemType Directory -Path $CacheDir -Force | Out-Null
}

# Dedicated profile dir - NOT the default Edge profile, so headless instances
# do not collide with the user's everyday Edge session.
$ProfileDir = Join-Path $env:LOCALAPPDATA "SAPNoteEdgeProfile"

# Locate msedge.exe
function Find-Edge {
    $candidates = @(
        "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
        "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
        "$env:LOCALAPPDATA\Microsoft\Edge\Application\msedge.exe"
    )
    foreach ($c in $candidates) {
        if ($c -and (Test-Path $c)) { return $c }
    }
    return $null
}

# Zero-pad note number to 10 digits if it is purely numeric.
function Format-NoteNumber($n) {
    $n = $n.Trim()
    if ($n -match '^\d+$') { return $n.PadLeft(10, '0') }
    return $n
}

# Read a file with shared access and retries, as UTF-8. Survives any lingering
# child-process handle on the temp output file after the main Edge process exits.
function Read-FileShared($path) {
    for ($i = 0; $i -lt 20; $i++) {
        try {
            $fs = [System.IO.File]::Open($path, [System.IO.FileMode]::Open,
                [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
            try {
                $sr = New-Object System.IO.StreamReader($fs, [System.Text.Encoding]::UTF8)
                return $sr.ReadToEnd()
            } finally {
                if ($sr) { $sr.Dispose() }
                $fs.Dispose()
            }
        } catch {
            Start-Sleep -Milliseconds 100
        }
    }
    return $null
}

# Extract the raw response body from a --dump-dom string.
# Edge wraps JSON in <pre>...</pre>; we pull that out and decode HTML entities.
# If no <pre> is present (e.g. an HTML login page), return the original text
# unchanged so login-redirect detection still works.
function Extract-Body($dom) {
    $m = [regex]::Match($dom, '(?s)<pre[^>]*>(.*?)</pre>')
    if ($m.Success) {
        $body = $m.Groups[1].Value
    } else {
        $body = $dom
    }
    # Decode the HTML entities that --dump-dom adds. &amp; MUST be decoded last,
    # otherwise e.g. "&lt;" -> "<" first, then "&amp;" would wrongly turn a
    # real "&lt;" in the source into "<".
    $body = $body -replace '&lt;', '<'
    $body = $body -replace '&gt;', '>'
    $body = $body -replace '&quot;', '"'
    $body = $body -replace '&#39;', "'"
    $body = $body -replace '&amp;', '&'
    return $body
}

# Try to fetch a note via headless Edge. Returns a hashtable:
#   @{ status = "ok"|"login"|"error"; body = <raw json or html>; msg = <info> }
# - "ok"    : got valid content (JSON or HTML), saved nothing - caller decides.
# - "login" : response looks like a SAP login redirect (session expired).
# - "error" : headless Edge failed to produce output (e.g. profile in use).
function Try-FetchNote($noteNum) {
    $apiUrl = "https://me.sap.com/backend/raw/sapnotes/Detail?q=$noteNum&isVTEnabled=false"
    if (-not (Test-Path $ProfileDir)) {
        return @{ status = "login"; body = ""; msg = "profile dir not found - need login" }
    }
    # SAML session in headless mode is flaky - a single --dump-dom run may
    # get a sad_cloud / login redirect even when the session is actually valid,
    # because each headless process is a fresh session and SAML state does not
    # always re-establish in time. Retry a few times before declaring failure.
    $maxRetries = 3
    for ($attempt = 1; $attempt -le $maxRetries; $attempt++) {
        $r = Try-FetchNoteOnce $noteNum $apiUrl
        if ($r.status -eq "ok") { return $r }
        if ($r.status -eq "error") { return $r }  # hard error, don't retry
        # status = "login": maybe SAML flakiness. Retry after a short wait,
        # unless this was the last attempt.
        if ($attempt -lt $maxRetries) {
            Write-Output "  (attempt $attempt got login redirect - SAML may be flaky, retrying in 3s...)"
            Start-Sleep -Seconds 3
        }
    }
    return @{ status = "login"; body = ""; msg = "login redirect after $maxRetries attempts - session likely expired" }
}

# Single attempt to fetch a note via headless Edge. Returns a hashtable:
#   @{ status = "ok"|"login"|"error"; body = <raw json or html>; msg = <info> }
function Try-FetchNoteOnce($noteNum, $apiUrl) {

    $tmpOut = [System.IO.Path]::GetTempFileName()
    $tmpErr = [System.IO.Path]::GetTempFileName()
    $exitCode = -1
    try {
        $args = @(
            "--headless=new",
            "--user-data-dir=`"$ProfileDir`"",
            "--disable-extensions",
            "--no-first-run",
            "--no-default-browser-check",
            # Allow third-party cookies - SAP's SAML SSO spans multiple domains
            # (me.sap.com, accounts.sap.com, authentication.eu11.hana.ondemand.com).
            # Without this, SAML callback fails with "InResponseTo ... no saved
            # authentication request" (the sad_cloud error page).
            "--third-party-cookie-allowed",
            "--disable-features=ThirdPartyCookiePhaseout",
            "--dump-dom",
            "`"$apiUrl`""
        )
        $argString = $args -join " "
        $p = Start-Process -FilePath $edge `
            -ArgumentList $argString `
            -RedirectStandardOutput $tmpOut `
            -RedirectStandardError $tmpErr `
            -PassThru -WindowStyle Hidden
        if (-not $p.WaitForExit(60000)) {
            try { $p.Kill() } catch {}
            Remove-Item $tmpOut, $tmpErr -ErrorAction SilentlyContinue
            return @{ status = "error"; body = ""; msg = "headless Edge did not exit within 60s" }
        }
        $exitCode = $p.ExitCode
        try { $p.Dispose() } catch {}
        Start-Sleep -Milliseconds 200
    } catch {
        Remove-Item $tmpOut, $tmpErr -ErrorAction SilentlyContinue
        return @{ status = "error"; body = ""; msg = "failed to launch headless Edge: $($_.Exception.Message)" }
    }

    $dom = ""
    if (Test-Path $tmpOut) {
        $dom = Read-FileShared $tmpOut
        if ($null -eq $dom) { $dom = "" }
    }
    $errText = ""
    if (Test-Path $tmpErr) { $errText = Read-FileShared $tmpErr }
    Remove-Item $tmpOut, $tmpErr -ErrorAction SilentlyContinue

    if ([string]::IsNullOrEmpty($dom)) {
        return @{ status = "error"; body = ""; msg = "no output (exit $exitCode). stderr: $errText. Maybe profile in use." }
    }

    # Detect login redirect on the raw DOM (before extraction).
    $isLoginRedirect = $false
    if ($dom -match "oauth/authorize") { $isLoginRedirect = $true }
    elseif ($dom -match "locationAfterLogin") { $isLoginRedirect = $true }
    elseif ($dom -match "accounts\.sap\.com/saml2/idp/sso") { $isLoginRedirect = $true }
    elseif ($dom -match '<title>[^<]*Sign In[^<]*</title>') { $isLoginRedirect = $true }
    elseif ($dom -match 'id="logOnForm"') { $isLoginRedirect = $true }
    elseif ($dom -match 'data-pagetype="Login"') { $isLoginRedirect = $true }
    # SAP SAML auth error page (sad_cloud / InResponseTo) - session invalid.
    elseif ($dom -match "sad_cloud\.png") { $isLoginRedirect = $true }
    elseif ($dom -match "InResponseTo attribute") { $isLoginRedirect = $true }
    elseif ($dom -match "sapUiSraLoginLogo") { $isLoginRedirect = $true }

    if ($isLoginRedirect) {
        return @{ status = "login"; body = $dom; msg = "login redirect - session expired" }
    }

    # A bare "Internal Server Error" from the note API is a 500, NOT a login
    # redirect. SAP's backend returns 500 when the request reaches the API
    # unauthenticated (no valid session cookie attached) - but it can also mean
    # a genuine backend hiccup. Reporting it as "login" misleads the user into
    # re-logging in repeatedly when the real issue may be that the session
    # cookie never made it into the profile. Surface it as a distinct error so
    # the post-login self-check (which actually tests the session) can tell the
    # two apart.
    if ($dom -match "Internal Server Error") {
        return @{ status = "error"; body = $dom; msg = "API returned Internal Server Error (500) - likely unauthenticated, or backend error" }
    }

    $body = Extract-Body $dom

    # The note API's success response is always a JSON object. If the extracted
    # body is not valid JSON, the session is invalid - Edge served the SAP for Me
    # shell page, an error page, or some other HTML instead of the note. Treat
    # this as a login failure so the caller triggers re-login, rather than
    # silently saving a useless HTML skeleton and reporting success.
    $trimmed = $body.TrimStart()
    if (-not ($trimmed.StartsWith("{") -or $trimmed.StartsWith("["))) {
        return @{ status = "login"; body = $dom; msg = "response is not JSON - session invalid (got HTML page)" }
    }
    try {
        $null = $body | ConvertFrom-Json -ErrorAction Stop
    } catch {
        return @{ status = "login"; body = $dom; msg = "response is not valid JSON - session invalid (parse failed)" }
    }

    return @{ status = "ok"; body = $body; msg = "ok" }
}

# Save the fetched body to disk as <note>.json. The caller only passes bodies
# that already passed JSON validation in Try-FetchNoteOnce, so a non-JSON body
# here is a bug - refuse to write a useless HTML skeleton and surface the error
# instead of silently saving garbage.
function Save-Note($noteNum, $body) {
    $isJson = $false
    $trimmed = $body.TrimStart()
    if ($trimmed.StartsWith("{") -or $trimmed.StartsWith("[")) {
        try { $null = $body | ConvertFrom-Json -ErrorAction Stop; $isJson = $true } catch { $isJson = $false }
    }
    if (-not $isJson) {
        Write-Output "ERROR: refusing to save non-JSON body for note $noteNum (session likely invalid). Nothing written."
        return $false
    }
    $outFile = Join-Path $CacheDir "$noteNum.json"
    [System.IO.File]::WriteAllText($outFile, $body, (New-Object System.Text.UTF8Encoding($false)))
    Write-Output "Saved note JSON to: $outFile"
    Write-Output "Content length: $($body.Length) chars"
    return $true
}

# Count Edge processes using OUR dedicated profile (by command line).
# Used to detect when the login window has been closed by the user.
function Count-ProfileEdgeProcs {
    try {
        $procs = Get-CimInstance Win32_Process -Filter "Name='msedge.exe'" -ErrorAction Stop
    } catch { return 0 }
    $count = 0
    foreach ($p in $procs) {
        if ($p.CommandLine -and ($p.CommandLine -like "*SAPNoteEdgeProfile*")) { $count++ }
    }
    return $count
}

# Gracefully close all Edge processes using OUR dedicated profile. We ask each
# process to close its main window (CloseMainWindow) and give Edge time to exit
# on its own - this is the path that flushes HttpOnly session cookies to the
# profile's cookie store on shutdown. Only processes that refuse to exit after
# the grace period are force-killed. Force-killing too early can lose cookies
# that have not yet been written to disk, which is exactly the failure mode we
# are working around.
function Close-ProfileEdgeGracefully {
    param([int]$GraceSeconds = 8)
    $procs = @()
    try {
        $procs = Get-CimInstance Win32_Process -Filter "Name='msedge.exe'" -ErrorAction Stop |
            Where-Object { $_.CommandLine -and ($_.CommandLine -like "*SAPNoteEdgeProfile*") }
    } catch { return }

    # Ask each process to close its window normally. CIM objects are not
    # Process objects, so re-fetch via Stop-Process-friendly Get-Process by Id.
    foreach ($p in $procs) {
        try {
            $proc = Get-Process -Id $p.ProcessId -ErrorAction Stop
            if ($proc.CloseMainWindow()) { Write-Output "  (asked Edge PID $($p.ProcessId) to close)" }
        } catch {}
    }

    # Wait up to $GraceSeconds for them to exit on their own.
    $deadline = 0
    while ($deadline -lt $GraceSeconds) {
        Start-Sleep -Seconds 1
        $deadline += 1
        if ((Count-ProfileEdgeProcs) -eq 0) {
            Write-Output "  (Edge exited cleanly after ${deadline}s - cookies flushed)"
            return
        }
    }

    # Still running - force kill as a last resort.
    Write-Output "  (Edge did not exit in ${GraceSeconds}s, force-killing)"
    foreach ($p in $procs) {
        try { Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop } catch {}
    }
    Start-Sleep -Seconds 2
}

# Open the windowed Edge login window on the dedicated profile and wait for the
# USER to close it themselves. Returns $true if the window appeared and was then
# closed (cookies flushed), $false if it never appeared or timed out. Factored
# out so batch mode can log in ONCE and then fetch many notes without
# re-prompting - the same code path serves single-note and batch calls.
#
# CRITICAL: while the login window is open we do NOTHING that touches the
# profile (no headless probe). Chromium forbids two processes sharing one
# profile dir; a concurrent headless probe steals the profile lock and freezes
# the foreground login window. We only count profile Edge processes via WMI
# (no browser involved) until they hit zero, i.e. the user closed the window.
# A user-initiated close after a confirmed login lets Edge run its full
# shutdown and flush the HttpOnly session cookie to the profile's cookie store
# cleanly. The script NEVER closes the login window for the user.
function Open-LoginWindowAndWait {
    Write-Output ""
    Write-Output "Session expired or missing. Opening Edge for SAP login..."
    Write-Output "Profile dir: $ProfileDir"
    Write-Output ">>> An Edge window has opened at me.sap.com."
    Write-Output ">>> Log in to SAP there. Once you see you are logged in (the SAP for"
    Write-Output ">>> Me homepage shows your account, NOT a 'Sign In' button), CLOSE the"
    Write-Output ">>> Edge window YOURSELF. This script detects the login, then WAITS for"
    Write-Output ">>> you to close the window - it does NOT close it for you. Closing the"
    Write-Output ">>> window yourself after a confirmed login lets Edge flush the session"
    Write-Output ">>> cookie to disk cleanly, so the note fetch succeeds."
    Write-Output ""

    $null = Start-Process -FilePath $edge `
        -ArgumentList "--user-data-dir=`"$ProfileDir`"", "https://me.sap.com" `
        -PassThru

    # Wait for the Edge window to actually appear.
    $appeared = $false
    for ($i = 0; $i -lt 15; $i++) {
        Start-Sleep -Seconds 1
        if ((Count-ProfileEdgeProcs) -gt 0) { $appeared = $true; break }
    }
    if (-not $appeared) {
        Write-Output "ERROR: Edge login window never appeared. Aborting."
        return $false
    }

    Write-Output ""
    Write-Output ">>> Complete the SAP login in the Edge window."
    Write-Output ">>> Once you are logged in (homepage shows your account, NOT a 'Sign In'"
    Write-Output ">>> button), CLOSE the Edge window YOURSELF. This script is waiting for"
    Write-Output ">>> the window to close - it will then fetch the note automatically"
    Write-Output ">>> (closing the window yourself lets Edge save the session cookie cleanly)."
    Write-Output ">>> Waiting for the Edge window to be closed (up to 10 min)..."
    $closeTimeoutSec = 600
    $closeElapsed = 0
    while ($closeElapsed -lt $closeTimeoutSec) {
        Start-Sleep -Seconds 3
        $closeElapsed += 3
        if ((Count-ProfileEdgeProcs) -eq 0) {
            Write-Output "  (Edge window closed after ${closeElapsed}s - session cookie flushed)"
            return $true
        }
    }
    Write-Output "ERROR: Edge window was not closed within ${closeTimeoutSec}s."
    Write-Output "Close the Edge window and re-run this script to try again."
    Close-ProfileEdgeGracefully -GraceSeconds 4
    return $false
}

# Force-kill any Edge processes using OUR dedicated profile, to clear genuine
# leftovers (a headless Edge that did not exit) before a retry. Safe in batch
# mode because there is only ONE script process: during the fetch loop the
# login window is never open (we always wait for it to close before continuing),
# so any profile Edge alive here is a true leftover, not a window the user is
# interacting with. (This is the exact logic that, under the OLD concurrent
# two-instance misuse, killed the other instance's login window - which is why
# sap-note fetches must never run concurrently.)
function Clear-LeftoverProfileEdge {
    try {
        Get-CimInstance Win32_Process -Filter "Name='msedge.exe'" -ErrorAction Stop |
          Where-Object { $_.CommandLine -and ($_.CommandLine -like "*SAPNoteEdgeProfile*") } |
          ForEach-Object { try { Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop } catch {} }
        Start-Sleep -Seconds 2
    } catch {}
}

# --- No note numbers: print usage ---
if ($NoteNumbers.Count -eq 0) {
    Write-Output "SAP Note fetcher (headless Edge)"
    Write-Output ""
    Write-Output "Usage:"
    Write-Output "  powershell -ExecutionPolicy Bypass -File get_sapnote.ps1 <noteNumber> [<noteNumber> ...]"
    Write-Output ""
    Write-Output "  Accepts one or more note numbers. Cached notes are skipped (no network);"
    Write-Output "  the rest are fetched SERIALLY against one shared Edge profile. If the"
    Write-Output "  SAP session is expired, an Edge login window opens ONCE - after you log"
    Write-Output "  in and CLOSE that window, all remaining notes are fetched automatically."
    Write-Output ""
    Write-Output "  DO NOT run multiple instances of this script concurrently: they share one"
    Write-Output "  Edge profile dir and Chromium forbids two processes using it at once"
    Write-Output "  (one instance's login window would get force-killed by the other). To"
    Write-Output "  fetch many notes, pass them all in a SINGLE call (serial internally) -"
    Write-Output "  never launch parallel processes."
    Write-Output ""
    Write-Output "  Examples:"
    Write-Output "    powershell -ExecutionPolicy Bypass -File get_sapnote.ps1 3021593"
    Write-Output "    powershell -ExecutionPolicy Bypass -File get_sapnote.ps1 3152102 3570335 2743317"
    Write-Output ""
    Write-Output "  Profile dir: $ProfileDir"
    Write-Output "  Output: sap-notes/<noteNumber>.json under this script's dir (local viewing only)."
    exit 0
}

$edge = Find-Edge
if (-not $edge) {
    Write-Output "ERROR: msedge.exe not found. Install Microsoft Edge."
    exit 1
}

# --- Batch fetch: serialize all notes through one profile, log in at most once ---
# Zero-pad every note number, then split into cached (skip) vs to-fetch.
$notes = @()
foreach ($n in $NoteNumbers) {
    $n = $n.Trim()
    if ($n -ne "") { $notes += (Format-NoteNumber $n) }
}
if ($notes.Count -eq 0) {
    Write-Output "ERROR: no valid note numbers supplied."
    exit 1
}

$cached = @()
$toFetch = @()
foreach ($noteNum in $notes) {
    $cacheFile = Join-Path $CacheDir "$noteNum.json"
    if (Test-Path $cacheFile) { $cached += $noteNum } else { $toFetch += $noteNum }
}
if ($cached.Count -gt 0) {
    Write-Output "Cached (skipping fetch): $($cached -join ', ')"
}
if ($toFetch.Count -eq 0) {
    Write-Output "All notes already cached. Nothing to fetch."
    exit 0
}

Write-Output ""
Write-Output "Auto-fetch: $($toFetch.Count) note(s): $($toFetch -join ', ')"
Write-Output "Step 1: try headless fetch with existing session..."

# Session state tracked across notes so we log in at most once per expiry event.
$sessionValid  = $false   # set true after any successful headless fetch
$loginOpened   = $false   # the login window has been opened at least once
$sessionBroken = $false   # login window failed/timed out - session unusable

$okCount = 0
$failCount = 0
$failedNotes = @()

foreach ($noteNum in $toFetch) {
    Write-Output ""
    Write-Output "--- $noteNum ---"

    # If a prior login attempt failed (window never appeared / timed out), the
    # session is unusable - don't keep hitting the API, just skip the rest.
    if ($sessionBroken) {
        Write-Output "SKIPPED: session unusable (prior login failed)."
        $failCount++
        $failedNotes += $noteNum
        continue
    }

    $result = Try-FetchNote $noteNum

    # error: likely a leftover headless Edge holding the profile. Clear it and
    # retry once. (In single-process batch mode this can only be a true leftover
    # - the login window is never open during the fetch loop.)
    if ($result.status -eq "error") {
        Write-Output "WARN: $($result.msg) - clearing leftover profile Edge and retrying..."
        Clear-LeftoverProfileEdge
        $result = Try-FetchNote $noteNum
    }

    # login: session expired. Open the login window ONCE (or again only if we
    # had a valid session before - a genuine mid-batch re-expiry). Do NOT reopen
    # when we already opened and never succeeded - that prevents a re-login
    # loop; the user should re-run instead.
    if ($result.status -eq "login") {
        $shouldOpen = (-not $loginOpened) -or $sessionValid
        if ($shouldOpen) {
            $sessionValid = $false
            $windowClosed = Open-LoginWindowAndWait
            $loginOpened = $true
            if ($windowClosed) {
                Start-Sleep -Seconds 1  # brief settle for the cookie flush
                Write-Output "Session is logged in. Fetching $noteNum..."
                $result = Try-FetchNote $noteNum
            } else {
                $sessionBroken = $true
                $result = @{ status = "error"; body = ""; msg = "login window failed/timed out" }
            }
        }
    }

    switch ($result.status) {
        "ok" {
            $sessionValid = $true
            $saved = Save-Note $noteNum $result.body
            if ($saved) { Write-Output "OK: $noteNum"; $okCount++ }
            else { Write-Output "FAILED: $noteNum (save error)"; $failCount++; $failedNotes += $noteNum }
        }
        "login" {
            Write-Output "FAILED: $noteNum - session still invalid after login."
            Write-Output "  The SAP login may not have completed before the window was closed,"
            Write-Output "  or the session cookie did not flush to the profile."
            $failCount++
            $failedNotes += $noteNum
        }
        "error" {
            Write-Output "FAILED: $noteNum - $($result.msg)"
            $failCount++
            $failedNotes += $noteNum
        }
    }
}

Write-Output ""
Write-Output "=== Batch summary ==="
Write-Output "Fetched OK : $okCount"
if ($cached.Count -gt 0) { Write-Output "From cache : $($cached.Count) ($($cached -join ', '))" }
Write-Output "Failed     : $failCount"
if ($failedNotes.Count -gt 0) { Write-Output "Failed notes: $($failedNotes -join ', ')" }

if ($failCount -gt 0) { exit 1 } else { exit 0 }
