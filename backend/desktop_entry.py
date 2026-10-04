import sys

if __name__ == "__main__":
    if sys.argv[1:] == ["--parse-import"]:
        from backend.app.import_worker import main
        main()
    elif sys.argv[1:] in (["--retrieve-private-market"], ["--check-private-market"]):
        from backend.app.yfinance_worker import main
        main(check_only=sys.argv[1] == "--check-private-market")
    else:
        from backend.app.entrypoint import run
        run()
