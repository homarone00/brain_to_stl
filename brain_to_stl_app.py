if __name__ == "__main__":
    import multiprocessing

    multiprocessing.freeze_support()

    from brain_to_stl.gui import main as gui_main

    gui_main()
