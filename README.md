Brain to STL
============

A standalone desktop GUI for:

1. Selecting an input `.nii`/`.nii.gz` MRI volume or a DICOM series folder.
2. Converting DICOM to NIfTI when needed.
3. Running HD-BET skull stripping.
4. Converting the skull-stripped NIfTI volume into a binary STL mesh for 3D printing.

The app uses HD-BET through its command line interface, then meshes the resulting brain volume with marching cubes.

Setup With uv
-------------

Install `uv`, then run:

```powershell
.\run.ps1
```

The script automatically creates/updates the local environment, installs the app, installs HD-BET, and launches the GUI.

You can also run the same steps manually:

```powershell
uv sync
uv run brain-to-stl
```

Setup With pip
--------------

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -e .
```

Run
---

If you used `uv`:

```powershell
uv run brain-to-stl
```

If you used `pip` inside an activated virtual environment:

```powershell
brain-to-stl
```

Or:

```powershell
python -m brain_to_stl.gui
```

In the GUI:

- Choose the input NIfTI file or DICOM series folder.
- Choose an output folder, or keep the automatic folder.
- Click **Run**.
- Use the napari buttons to inspect the original NIfTI, the skull-stripped NIfTI, or the STL mesh.

The app automatically uses CUDA for HD-BET when PyTorch detects an available CUDA GPU. Otherwise it falls back to CPU. STL thresholding, mild mesh simplification, and mesh cleanup use built-in defaults.

For DICOM input, select the folder containing one DICOM series. If the folder contains multiple series, the app uses the largest series and writes an intermediate `*_input.nii.gz` file in the output folder.

Outputs
-------

For an input like `scan.nii.gz`, the app creates:

- `scan_brain.nii.gz`: HD-BET skull-stripped NIfTI.
- `scan_brain.stl`: printable binary STL.

Build A Single Executable
-------------------------

```powershell
.\build_exe.ps1
```

The executable will be written under `dist\BrainToSTL.exe`.

The build script sets the app icon, regenerates the PyInstaller spec, and explicitly collects HD-BET, nnU-Net, SimpleITK, napari, Qt, vispy, pydantic, imageio, and meshio modules. This matters because nnU-Net and napari load many classes dynamically at runtime.

If the app opens duplicate GUI windows during HD-BET inference, rebuild the executable from the latest source. The launcher includes the Windows multiprocessing guard required by PyInstaller and nnU-Net worker processes.

Notes
-----

HD-BET is a deep-learning tool and can be slow on CPU. GPU use is faster, but requires a working PyTorch/CUDA setup. Input files should be 3D NIfTI MRI volumes or DICOM folders representing a single 3D series; 4D sequences should be split into individual volumes first.
