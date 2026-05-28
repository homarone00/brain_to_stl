BrainToSTL
==========

Turn a brain scan into a 3D-printable brain. Because sometimes the correct answer to medical imaging is: "what if I could hold this?"

BrainToSTL is a Windows-friendly desktop app that takes a NIfTI file or a DICOM series folder, skull-strips it with HD-BET, turns the result into an STL mesh, and simplifies it a little so your slicer does not file a complaint.

What It Does
------------

- Opens `.nii`, `.nii.gz`, or a DICOM series folder.
- Converts DICOM to NIfTI when needed.
- Runs HD-BET skull stripping.
- Uses CUDA automatically when PyTorch sees a CUDA GPU.
- Falls back to CPU when CUDA is not available.
- Converts the skull-stripped brain to STL.
- Applies mild mesh simplification.

Quick Start
-----------

Install `uv`, then run:

```powershell
.\run.ps1
```

That creates or updates the local environment, installs the entire medical-imaging parade, and launches the app.

Manual `uv` version:

```powershell
uv sync
uv run brain-to-stl
```

Pip Version
-----------

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -e .
brain-to-stl
```

Using The App
-------------

1. Click `NIfTI` or `DICOM folder`.
2. Pick an output folder, or let the app choose one.
3. Click `Run`.
4. Wait while HD-BET thinks very deep thoughts.
5. Print responsibly. Tiny desk brains are powerful objects.

Outputs
-------

For `scan.nii.gz`, BrainToSTL writes:

- `scan_brain.nii.gz`: skull-stripped NIfTI.
- `scan_brain.stl`: printable STL mesh.

For DICOM input, it also writes:

- `<dicom_folder>_input.nii.gz`: intermediate converted NIfTI.

If a DICOM folder contains multiple series, the app uses the largest series. This is usually the main scan, but please check the output before trusting anything important.

Build A Standalone EXE
----------------------

```powershell
.\build_exe.ps1
```

The executable appears here:

```powershell
dist\BrainToSTL.exe
```

The build script does a few unglamorous but necessary things:

- Sets the app icon.
- Regenerates the PyInstaller spec.
- Bundles HD-BET, nnU-Net, SimpleITK, fast-simplification, and friends.
- Adds PyInstaller-friendly handling for Windows multiprocessing.

Release On GitHub
-----------------

Do not commit the built `.exe`. Put generated files in `.gitignore`, then upload the exe as a GitHub Release asset.

Typical flow:

```powershell
.\build_exe.ps1
git add README.md pyproject.toml uv.lock run.ps1 build_exe.ps1 brain_to_stl brain_to_stl_app.py assets .gitignore
git commit -m "Prepare Windows release"
git push
git tag v0.1.0
git push origin v0.1.0
```

Then create a GitHub release in the browser and upload:

```powershell
dist\BrainToSTL.exe
```

Notes From The Imaging Mines
----------------------------

HD-BET is deep-learning software. It can be slow on CPU. CUDA is faster, but only if your PyTorch/CUDA setup is healthy.

Input should be a 3D NIfTI volume or a DICOM folder representing one 3D series. If you have a 4D scan, split it first.

PyInstaller is wonderful, but packaging deep-learning medical imaging tools is still a small negotiation with the universe. If the standalone app behaves strangely, rebuild from a clean source tree with:

```powershell
.\build_exe.ps1
```

Not Medical Advice
------------------

This is a visualization and 3D-printing utility, not a diagnostic device. Please do not make clinical decisions based on a charming plastic brain.
