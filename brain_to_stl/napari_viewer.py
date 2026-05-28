from __future__ import annotations

import sys
from pathlib import Path


def open_nifti(path: Path) -> None:
    import napari
    import nibabel as nib
    import numpy as np

    _ensure_qapp()
    img = nib.as_closest_canonical(nib.load(str(path)))
    data = np.asarray(img.get_fdata(dtype=np.float32))
    if data.ndim == 4:
        data = data[..., 0]
    if data.ndim != 3:
        raise ValueError(f"Expected a 3D NIfTI volume, got shape {data.shape}.")

    data = np.moveaxis(data, -1, 0)
    data = np.nan_to_num(data, copy=False)
    spacing = img.header.get_zooms()[:3]
    scale = (float(spacing[2]), float(spacing[1]), float(spacing[0]))

    viewer = napari.Viewer(title=f"Brain to STL - {path.name}")
    viewer.add_image(
        data,
        name=path.name,
        colormap="gray",
        contrast_limits=_contrast_limits(data),
        scale=scale,
    )
    viewer.dims.current_step = (data.shape[0] // 2, data.shape[1] // 2, data.shape[2] // 2)
    napari.run()


def open_stl(path: Path) -> None:
    import meshio
    import napari
    import numpy as np

    _ensure_qapp()
    mesh = meshio.read(path)
    faces = mesh.cells_dict.get("triangle")
    if faces is None:
        for cell_block in mesh.cells:
            if cell_block.data.shape[1] == 3:
                faces = cell_block.data
                break
    if faces is None:
        raise ValueError(f"No triangular faces found in STL file: {path}")

    values = np.zeros(len(mesh.points), dtype=np.float32)
    viewer = napari.Viewer(title=f"Brain to STL - {path.name}")
    viewer.add_surface((mesh.points, faces, values), name=path.name)
    napari.run()


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 2 or argv[0] not in {"nifti", "stl"}:
        print("Usage: napari_viewer.py nifti|stl PATH", file=sys.stderr)
        return 2

    kind, raw_path = argv
    path = Path(raw_path)
    if kind == "nifti":
        open_nifti(path)
    else:
        open_stl(path)
    return 0


def _contrast_limits(data) -> tuple[float, float]:
    import numpy as np

    array = np.asarray(data)
    finite = array[np.isfinite(array)]
    if finite.size == 0:
        return (0.0, 1.0)
    nonzero = finite[finite != 0]
    sample = nonzero if nonzero.size else finite
    low, high = np.percentile(sample, [1, 99.5])
    if low == high:
        high = low + 1
    return (float(low), float(high))


def _ensure_qapp() -> None:
    from napari._qt.qt_event_loop import get_qapp

    get_qapp()


if __name__ == "__main__":
    raise SystemExit(main())
