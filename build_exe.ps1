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
    --collect-all PyQt6 `
    --collect-all SimpleITK `
    --collect-all app_model `
    --collect-all fast_simplification `
    --collect-all imageio `
    --collect-all magicgui `
    --collect-all meshio `
    --collect-all napari `
    --collect-all napari_builtins `
    --collect-all nnunetv2 `
    --collect-all npe2 `
    --collect-all psygnal `
    --collect-all pydantic `
    --collect-all pydantic_core `
    --collect-all qtpy `
    --collect-all superqt `
    --collect-all vispy `
    --collect-submodules napari.layers `
    --collect-submodules napari.components `
    --collect-submodules nnunetv2.training.nnUNetTrainer `
    --copy-metadata imageio `
    --copy-metadata napari `
    --hidden-import brain_to_stl.napari_viewer `
    brain_to_stl_app.py
