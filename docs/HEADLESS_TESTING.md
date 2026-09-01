# Headless and visual testing

## Full test suite

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
$env:PYTHONPATH = (Resolve-Path src)
python -m compileall -q src scripts run_opa.py
python scripts/check_public_release.py
python -m unittest discover -s src -p "test_*.py"
```

## Theme/language/module smoke test

```powershell
python scripts/headless_smoke.py
python scripts/headless_smoke.py --screenshot visual_qa.png
```

The screenshot command uses synthetic data and must not be run while an Admin session is unlocked.

## Windows scaling matrix

Run each command in a fresh process because Qt reads scale configuration at startup:

```powershell
foreach ($scale in "1", "1.25", "1.5", "2") {
    $env:QT_SCALE_FACTOR = $scale
    python scripts/headless_smoke.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
Remove-Item Env:QT_SCALE_FACTOR -ErrorAction SilentlyContinue
```

Automated tests check accessibility and containment of the main module tabs and Settings controls. Human release QA should still inspect Normal/Retro and Azerbaijani/English at 1366×768 and 1920×1080, including every nested page, dialogs, tables, context menus, and long text.
