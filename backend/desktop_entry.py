import sys

if __name__ == "__main__":
    if sys.argv[1:] == ["--parse-import"]:
        from backend.app.import_worker import main
        main()
    else:
        from backend.app.entrypoint import run
        run()
