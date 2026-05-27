from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .pipeline import PipelineConfig, default_output_dir, run_pipeline, validate_nifti_path


class BrainToStlApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Brain to STL")
        self.geometry("820x620")
        self.minsize(720, 520)

        self.input_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Select a NIfTI file to begin.")
        self._log_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self._worker: threading.Thread | None = None

        self._build_ui()
        self.after(100, self._drain_log_queue)

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        main = ttk.Frame(self, padding=16)
        main.grid(row=0, column=0, sticky="nsew")
        main.columnconfigure(1, weight=1)

        ttk.Label(main, text="Input NIfTI").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(main, textvariable=self.input_var).grid(row=0, column=1, sticky="ew")
        ttk.Button(main, text="Browse", command=self._browse_input).grid(row=0, column=2, padx=(8, 0))

        ttk.Label(main, text="Output folder").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(10, 0))
        ttk.Entry(main, textvariable=self.output_var).grid(row=1, column=1, sticky="ew", pady=(10, 0))
        ttk.Button(main, text="Browse", command=self._browse_output).grid(row=1, column=2, padx=(8, 0), pady=(10, 0))

        log_frame = ttk.Frame(self, padding=(16, 0, 16, 0))
        log_frame.grid(row=1, column=0, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = tk.Text(log_frame, height=14, wrap="word", state="disabled")
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scrollbar.set)

        footer = ttk.Frame(self, padding=16)
        footer.grid(row=2, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        ttk.Label(footer, textvariable=self.status_var).grid(row=0, column=0, sticky="w")
        self.run_button = ttk.Button(footer, text="Run", command=self._run)
        self.run_button.grid(row=0, column=1, sticky="e")

    def _browse_input(self) -> None:
        path = filedialog.askopenfilename(
            title="Select input NIfTI",
            filetypes=[("NIfTI files", "*.nii *.nii.gz"), ("All files", "*.*")],
        )
        if path:
            self.input_var.set(path)
            self.output_var.set(str(default_output_dir(Path(path))))

    def _browse_output(self) -> None:
        path = filedialog.askdirectory(title="Select output folder")
        if path:
            self.output_var.set(path)

    def _run(self) -> None:
        if self._worker and self._worker.is_alive():
            return

        try:
            input_nifti = validate_nifti_path(self.input_var.get())
            output_dir = Path(self.output_var.get() or default_output_dir(input_nifti))
            config = PipelineConfig(
                input_nifti=input_nifti,
                output_dir=output_dir,
            )
        except Exception as exc:
            messagebox.showerror("Invalid settings", str(exc))
            return

        self._clear_log()
        self.status_var.set("Running...")
        self.run_button.configure(state="disabled")
        self._worker = threading.Thread(target=self._worker_run, args=(config,), daemon=True)
        self._worker.start()

    def _worker_run(self, config: PipelineConfig) -> None:
        try:
            result = run_pipeline(config, log=lambda msg: self._log_queue.put(("log", msg)))
            self._log_queue.put(("done", f"Created STL: {result.stl_file}"))
        except Exception as exc:
            self._log_queue.put(("error", str(exc)))

    def _drain_log_queue(self) -> None:
        while True:
            try:
                kind, message = self._log_queue.get_nowait()
            except queue.Empty:
                break

            if kind == "log":
                self._append_log(message)
            elif kind == "done":
                self._append_log(message)
                self.status_var.set("Finished.")
                self.run_button.configure(state="normal")
                messagebox.showinfo("Finished", message)
            elif kind == "error":
                self._append_log(f"ERROR: {message}")
                self.status_var.set("Failed.")
                self.run_button.configure(state="normal")
                messagebox.showerror("Pipeline failed", message)

        self.after(100, self._drain_log_queue)

    def _append_log(self, message: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")


def main() -> None:
    app = BrainToStlApp()
    app.mainloop()


if __name__ == "__main__":
    main()
