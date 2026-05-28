if __name__ == "__main__":
    import multiprocessing
    import sys

    multiprocessing.freeze_support()

    if len(sys.argv) >= 2 and sys.argv[1] == "--napari":
        from brain_to_stl.napari_viewer import main

        raise SystemExit(main(sys.argv[2:]))

    from brain_to_stl.gui import main as gui_main

    gui_main()
