$ErrorActionPreference = "Stop"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is not installed. Install it from https://docs.astral.sh/uv/ and run this script again."
}

uv sync --extra build
uv run python -m compileall -j 8 .
if (Test-Path BrainToSTL.spec) {
    Remove-Item -LiteralPath BrainToSTL.spec -Force
}
uv run pyinstaller `
    --clean `
    --noconsole `
    --onefile `
    --name BrainToSTL `
    --icon assets\app_icon.ico `
    --add-data "assets\app_icon.ico;assets" `
    --collect-all HD_BET `
    --collect-all SimpleITK `
    --collect-all fast_simplification `
    --collect-all nnunetv2 `
    --collect-submodules nnunetv2.training.nnUNetTrainer `
    brain_to_stl_app.py
