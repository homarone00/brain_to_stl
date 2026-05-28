BrainToSTL
==========

Turn a brain scan into a 3D-printable brain. Because sometimes the correct answer to medical imaging is: "what if I could hold this?" or "I really need to keep my 3D printer on 24/7!"

BrainToSTL is a Windows-friendly desktop app that takes a NIfTI file or a DICOM series folder, skull-strips it with HD-BET, turns the result into an STL mesh, and simplifies it a little so your slicer does not file a complaint.
Mac and Linux support might, perhaps, maybe, arrive later on, if the PhD decides to spare me.

_blinks “please help me” in Morse code_

What it can do
------------

- Opens `.nii`, `.nii.gz`, or a DICOM series folder.
- Converts DICOM to NIfTI when needed.
- Runs HD-BET skull stripping.
- Uses CUDA automatically when PyTorch sees a CUDA GPU.
- Falls back to CPU when CUDA is not available.
- Converts the skull-stripped brain to STL.
- Applies mild mesh simplification.

What it can't do
------------
- Save you from 1000 angry frogs
- Make your brain more beautiful
- Print a new functioning brain if you lost yours at the grocery store

Quick Start
-----------

Install `uv`, then run:

```powershell
.\run.ps1
```

That creates or updates the local environment, installs the entire medical-imaging parade (like 1000 files), and launches the app.

Manual `uv` version:

```powershell
uv sync
uv run brain-to-stl
```

Pip Version
-----------

do not use pip

Using The App
-------------

1. Click `NIfTI` or `DICOM folder`.
2. Pick you input brain file/folder
2. Pick an output folder, or let the app choose one.
3. Click `Run`.
4. Wait while HD-BET thinks very deep thoughts.
5. Print responsibly. Tiny desk brains are powerful objects. For best results, print it at 4× scale and pretend this was always the plan.

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
DO NOT READ THIS! I WROTE THIS FOR MYSELF!

STOP!

STOP!
```powershell
.\build_exe.ps1
```

The executable appears here:

```powershell
dist\BrainToSTL.exe
```
