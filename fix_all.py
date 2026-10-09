with open("multiace/web/backend/main.py", "r") as f:
    content = f.read()
content = content.replace('MULTIACE_WEB_VERSION   default "0.1.0""""', 'MULTIACE_WEB_VERSION   default "0.1.0"\\n"""')
with open("multiace/web/backend/main.py", "w") as f:
    f.write(content)

with open("tests/test_backend_config_dir.py", "r") as f:
    content = f.read()
# Replace the bad test part
bad_import = """        import os
        expected_missing = os.path.abspath("/nonexistent/printer_data/config")"""
good_import = """        expected_missing = os.path.abspath("/nonexistent/printer_data/config")"""
content = content.replace(bad_import, good_import)
with open("tests/test_backend_config_dir.py", "w") as f:
    f.write(content)
