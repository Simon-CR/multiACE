with open("tests/test_backend_config_dir.py", "r") as f:
    content = f.read()

old_case_a = """        # Case A: non-existent directory
        os.environ["MULTIACE_CONFIG_DIR"] = "/nonexistent/printer_data/config"
        main = _reload_main()
        assert main._CFG_DIR == expected_default, (
            f"Expected fallback to {expected_default} for non-existent path, got {main._CFG_DIR}"
        )
        print("[ok]   non-existent MULTIACE_CONFIG_DIR falls back to default")"""

new_case_a = """        # Case A: non-existent directory
        os.environ["MULTIACE_CONFIG_DIR"] = "/nonexistent/printer_data/config"
        main = _reload_main()
        import os
        expected_missing = os.path.abspath("/nonexistent/printer_data/config")
        assert main._CFG_DIR == expected_missing, (
            f"Expected {expected_missing} for non-existent path, got {main._CFG_DIR}"
        )
        print("[ok]   non-existent MULTIACE_CONFIG_DIR respects env value directly")"""

content = content.replace(old_case_a, new_case_a)

with open("tests/test_backend_config_dir.py", "w") as f:
    f.write(content)
