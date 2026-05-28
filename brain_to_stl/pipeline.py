from __future__ import annotations

import contextlib
import shutil
import shlex
import subprocess
import sys
import sysconfig
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


LogFn = Callable[[str], None]


@dataclass(frozen=True)
class PipelineConfig:
    input_path: Path
    output_dir: Path
    hdbet_command: str = "hd-bet"
    threshold: float | None = None
    keep_largest_component: bool = True
    simplification_reduction: float = 0.25
    step_size: int = 1


@dataclass(frozen=True)
class PipelineResult:
    prepared_nifti: Path
    skull_stripped_nifti: Path
    stl_file: Path


def run_pipeline(config: PipelineConfig, log: LogFn = print) -> PipelineResult:
    input_path = config.input_path.resolve()
    output_dir = config.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    prepared_nifti = prepare_input_nifti(input_path, output_dir, log)
    output_stem = _input_stem(input_path)
    brain_nifti = output_dir / f"{output_stem}_brain.nii.gz"
    stl_file = output_dir / f"{output_stem}_brain.stl"

    log(f"Input: {input_path}")
    log(f"Prepared NIfTI: {prepared_nifti}")
    log(f"Skull-stripped NIfTI: {brain_nifti}")
    run_hdbet(prepared_nifti, config, brain_nifti, log)

    log(f"STL output: {stl_file}")
    nifti_to_stl(
        brain_nifti,
        stl_file,
        threshold=config.threshold,
        keep_largest_component=config.keep_largest_component,
        simplification_reduction=config.simplification_reduction,
        step_size=config.step_size,
        log=log,
    )

    log("Done.")
    return PipelineResult(prepared_nifti=prepared_nifti, skull_stripped_nifti=brain_nifti, stl_file=stl_file)


def prepare_input_nifti(input_path: Path, output_dir: Path, log: LogFn) -> Path:
    if is_nifti_path(input_path):
        return input_path
    if input_path.is_dir():
        nifti_path = output_dir / f"{_input_stem(input_path)}_input.nii.gz"
        convert_dicom_series_to_nifti(input_path, nifti_path, log)
        return nifti_path
    raise ValueError("Please select a .nii/.nii.gz file or a DICOM series folder.")


def convert_dicom_series_to_nifti(dicom_dir: Path, nifti_path: Path, log: LogFn) -> None:
    try:
        import SimpleITK as sitk
    except ModuleNotFoundError as exc:
        raise RuntimeError("Missing DICOM dependency. Run: uv sync") from exc

    log("Reading DICOM series...")
    series_ids = sitk.ImageSeriesReader.GetGDCMSeriesIDs(str(dicom_dir))
    if not series_ids:
        raise ValueError(f"No DICOM series found in folder: {dicom_dir}")

    series_files = [
        (series_id, sitk.ImageSeriesReader.GetGDCMSeriesFileNames(str(dicom_dir), series_id))
        for series_id in series_ids
    ]
    series_id, file_names = max(series_files, key=lambda item: len(item[1]))
    if len(series_ids) > 1:
        log(f"Found {len(series_ids)} DICOM series; using largest series with {len(file_names)} files.")
    else:
        log(f"Found DICOM series with {len(file_names)} files.")

    reader = sitk.ImageSeriesReader()
    reader.MetaDataDictionaryArrayUpdateOn()
    reader.LoadPrivateTagsOn()
    reader.SetFileNames(file_names)
    image = reader.Execute()

    log(f"Writing DICOM conversion: {nifti_path}")
    sitk.WriteImage(image, str(nifti_path))


def run_hdbet(input_nifti: Path, config: PipelineConfig, output_nifti: Path, log: LogFn) -> None:
    device = detect_hdbet_device()
    hdbet_args = ["-i", str(input_nifti), "-o", str(output_nifti), "-device", device, "--disable_tta"]

    log(f"Running HD-BET on {device.upper()}...")
    command = resolve_hdbet_command(config.hdbet_command)
    if command is None:
        log(f"{config.hdbet_command} " + " ".join(shlex.quote(part) for part in hdbet_args))
        run_hdbet_in_process(hdbet_args, log)
    else:
        command.extend(hdbet_args)
        log(" ".join(shlex.quote(part) for part in command))
        run_hdbet_subprocess(command, config, log)

    if not output_nifti.exists():
        raise RuntimeError(
            "HD-BET finished, but the expected skull-stripped NIfTI was not created."
        )


def run_hdbet_subprocess(command: list[str], config: PipelineConfig, log: LogFn) -> None:
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"Could not find HD-BET command '{config.hdbet_command}'. "
            "Install dependencies with: uv sync"
        ) from exc

    assert process.stdout is not None
    for line in process.stdout:
        log(line.rstrip())

    return_code = process.wait()
    if return_code != 0:
        raise RuntimeError(f"HD-BET failed with exit code {return_code}.")


def run_hdbet_in_process(args: list[str], log: LogFn) -> None:
    try:
        from HD_BET.entry_point import main as hdbet_main
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "HD-BET is not bundled in this executable. Rebuild with the PyInstaller "
            "HD-BET collection options from the README."
        ) from exc

    original_argv = sys.argv[:]
    sys.argv = ["hd-bet", *args]
    try:
        with contextlib.redirect_stdout(_LogWriter(log)), contextlib.redirect_stderr(_LogWriter(log)):
            hdbet_main()
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
        if code:
            raise RuntimeError(f"HD-BET failed with exit code {code}.") from exc
    finally:
        sys.argv = original_argv


class _LogWriter:
    def __init__(self, log: LogFn) -> None:
        self.log = log
        self.buffer = ""

    def write(self, text: str) -> int:
        self.buffer += text
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            if line:
                self.log(line)
        return len(text)

    def flush(self) -> None:
        if self.buffer:
            self.log(self.buffer)
            self.buffer = ""


def resolve_hdbet_command(command_name: str) -> list[str] | None:
    if getattr(sys, "frozen", False):
        return None

    scripts_dir = Path(sysconfig.get_path("scripts"))
    candidates = [
        scripts_dir / f"{command_name}.exe",
        scripts_dir / command_name,
        shutil.which(command_name),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return [str(candidate)]

    return None


def detect_hdbet_device() -> str:
    try:
        import torch
    except ModuleNotFoundError:
        return "cpu"
    return "cuda" if torch.cuda.is_available() else "cpu"


def nifti_to_stl(
    nifti_path: Path,
    stl_path: Path,
    *,
    threshold: float | None = None,
    keep_largest_component: bool = True,
    simplification_reduction: float = 0.25,
    step_size: int = 1,
    log: LogFn = print,
) -> None:
    try:
        import nibabel as nib
        import numpy as np
        from skimage import measure
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Missing conversion dependency. Run: python -m pip install -e ."
        ) from exc

    log("Loading skull-stripped NIfTI...")
    img = nib.load(str(nifti_path))
    data = np.asarray(img.get_fdata(dtype=np.float32))
    if data.ndim != 3:
        raise ValueError(f"Expected a 3D NIfTI volume, got shape {data.shape}.")

    finite = np.isfinite(data)
    if not finite.any():
        raise ValueError("The NIfTI volume contains no finite voxels.")

    if threshold is None:
        positive = data[finite & (data > 0)]
        if positive.size == 0:
            raise ValueError("The skull-stripped image has no positive voxels to mesh.")
        threshold = float(max(np.percentile(positive, 5), positive.min()))
        log(f"Auto threshold: {threshold:g}")
    else:
        log(f"Threshold: {threshold:g}")

    mask = finite & (data > threshold)
    if keep_largest_component:
        log("Keeping largest connected component...")
        labels = measure.label(mask, connectivity=1)
        component_sizes = np.bincount(labels.ravel())
        if component_sizes.size <= 1:
            raise ValueError("No connected brain component was found.")
        component_sizes[0] = 0
        mask = labels == int(component_sizes.argmax())

    voxel_count = int(mask.sum())
    if voxel_count == 0:
        raise ValueError("The threshold produced an empty mask.")
    log(f"Meshing {voxel_count:,} voxels...")

    padded = np.pad(mask.astype(np.float32), 1, mode="constant")
    verts, faces, _normals, _values = measure.marching_cubes(
        padded,
        level=0.5,
        step_size=max(1, int(step_size)),
    )
    verts -= 1.0
    verts = nib.affines.apply_affine(img.affine, verts)
    verts, faces = simplify_mesh(
        verts,
        faces,
        target_reduction=simplification_reduction,
        log=log,
    )

    log(f"Writing STL mesh: {len(verts):,} vertices, {len(faces):,} faces...")
    write_binary_stl(stl_path, verts, faces)


def simplify_mesh(vertices, faces, *, target_reduction: float, log: LogFn):
    import numpy as np

    if target_reduction <= 0 or len(faces) < 10_000:
        return vertices, faces

    try:
        import fast_simplification
    except ModuleNotFoundError:
        log("Mesh simplification skipped: fast-simplification is not installed.")
        return vertices, faces

    target_reduction = min(max(float(target_reduction), 0.0), 0.85)
    original_faces = len(faces)
    log(f"Simplifying mesh by {target_reduction:.0%}...")
    try:
        simplified_vertices, simplified_faces = fast_simplification.simplify(
            np.asarray(vertices, dtype=np.float64),
            np.asarray(faces, dtype=np.uint32),
            target_reduction,
        )
    except Exception as exc:
        log(f"Mesh simplification skipped: {exc}")
        return vertices, faces

    if len(simplified_faces) == 0:
        log("Mesh simplification skipped: simplifier produced an empty mesh.")
        return vertices, faces

    log(f"Simplified mesh faces: {original_faces:,} -> {len(simplified_faces):,}")
    return simplified_vertices, simplified_faces


def write_binary_stl(stl_path: Path, vertices, faces) -> None:
    import numpy as np

    vertices = np.asarray(vertices, dtype=np.float32)
    faces = np.asarray(faces, dtype=np.int32)
    triangles = vertices[faces]

    normals = np.cross(
        triangles[:, 1] - triangles[:, 0],
        triangles[:, 2] - triangles[:, 0],
    )
    lengths = np.linalg.norm(normals, axis=1)
    nonzero = lengths > 0
    normals[nonzero] /= lengths[nonzero, None]
    normals[~nonzero] = 0

    with stl_path.open("wb") as f:
        header = b"Created by brain-to-stl".ljust(80, b" ")
        f.write(header)
        f.write(np.uint32(len(triangles)).tobytes())
        for normal, triangle in zip(normals.astype("<f4"), triangles.astype("<f4")):
            f.write(normal.tobytes())
            f.write(triangle.tobytes())
            f.write(np.uint16(0).tobytes())


def _nifti_stem(path: Path) -> str:
    name = path.name
    if name.endswith(".nii.gz"):
        return name[:-7]
    return path.stem


def _input_stem(path: Path) -> str:
    return _nifti_stem(path) if is_nifti_name(path) else path.name


def is_nifti_path(path: Path) -> bool:
    return path.is_file() and is_nifti_name(path)


def is_nifti_name(path: Path) -> bool:
    return path.name.endswith(".nii") or path.name.endswith(".nii.gz")


def default_output_dir(input_path: Path) -> Path:
    return input_path.parent / f"{_input_stem(input_path)}_brain_to_stl"


def validate_input_path(path: str) -> Path:
    input_path = Path(path)
    if not input_path.exists():
        raise FileNotFoundError(path)
    if is_nifti_path(input_path) or input_path.is_dir():
        return input_path
    raise ValueError("Please select a .nii/.nii.gz file or a DICOM series folder.")


def validate_nifti_path(path: str) -> Path:
    input_path = Path(path)
    if not is_nifti_path(input_path):
        raise ValueError("Please select a .nii or .nii.gz file.")
    return input_path
