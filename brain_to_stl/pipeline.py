from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


LogFn = Callable[[str], None]


@dataclass(frozen=True)
class PipelineConfig:
    input_nifti: Path
    output_dir: Path
    hdbet_command: str = "hd-bet"
    threshold: float | None = None
    keep_largest_component: bool = True
    step_size: int = 1


@dataclass(frozen=True)
class PipelineResult:
    skull_stripped_nifti: Path
    stl_file: Path


def run_pipeline(config: PipelineConfig, log: LogFn = print) -> PipelineResult:
    input_nifti = config.input_nifti.resolve()
    output_dir = config.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    brain_nifti = output_dir / f"{_nifti_stem(input_nifti)}_brain.nii.gz"
    stl_file = output_dir / f"{_nifti_stem(input_nifti)}_brain.stl"

    log(f"Input: {input_nifti}")
    log(f"Skull-stripped NIfTI: {brain_nifti}")
    run_hdbet(input_nifti, config, brain_nifti, log)

    log(f"STL output: {stl_file}")
    nifti_to_stl(
        brain_nifti,
        stl_file,
        threshold=config.threshold,
        keep_largest_component=config.keep_largest_component,
        step_size=config.step_size,
        log=log,
    )

    log("Done.")
    return PipelineResult(skull_stripped_nifti=brain_nifti, stl_file=stl_file)


def run_hdbet(input_nifti: Path, config: PipelineConfig, output_nifti: Path, log: LogFn) -> None:
    device = detect_hdbet_device()
    command = [config.hdbet_command, "-i", str(input_nifti), "-o", str(output_nifti)]
    command.extend(["-device", device, "--disable_tta"])

    log(f"Running HD-BET on {device.upper()}...")
    log(" ".join(shlex.quote(part) for part in command))
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
            "Install HD-BET with: python -m pip install -e .[hdbet]"
        ) from exc

    assert process.stdout is not None
    for line in process.stdout:
        log(line.rstrip())

    return_code = process.wait()
    if return_code != 0:
        raise RuntimeError(f"HD-BET failed with exit code {return_code}.")
    if not output_nifti.exists():
        raise RuntimeError(
            "HD-BET finished, but the expected skull-stripped NIfTI was not created."
        )


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

    log(f"Writing STL mesh: {len(verts):,} vertices, {len(faces):,} faces...")
    write_binary_stl(stl_path, verts, faces)


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


def default_output_dir(input_nifti: Path) -> Path:
    return input_nifti.parent / f"{_nifti_stem(input_nifti)}_brain_to_stl"


def validate_nifti_path(path: str) -> Path:
    nifti = Path(path)
    if not nifti.exists():
        raise FileNotFoundError(path)
    if not (nifti.name.endswith(".nii") or nifti.name.endswith(".nii.gz")):
        raise ValueError("Please select a .nii or .nii.gz file.")
    return nifti
