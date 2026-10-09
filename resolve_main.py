import re

with open("multiace/web/backend/main.py", "r") as f:
    content = f.read()

# Resolve docstring conflict
docstring_conflict = """<<<<<<< HEAD
  MOONRAKER_URL          default http://127.0.0.1:7125
  MULTIACE_CONFIG_DIR    printer_data/config directory
  MULTIACE_PRINTER_DATA  printer data root
  MULTIACE_CFG_PATH      legacy explicit config-file override
  MULTIACE_FRONTEND_DIR  default ../frontend (relative to this file)
  MULTIACE_MANAGED       set to 1 when the platform owns installation/updates
  MULTIACE_MANAGED_MARKER durable neutral managed-install marker path
  MULTIACE_WEB_VERSION   default "0.1.0"
=======
  MOONRAKER_URL                 default http://127.0.0.1:7125
  MULTIACE_CONFIG_DIR           directory holding printer.cfg (default discovered via printer_data/config)
  MULTIACE_CFG_PATH             default <MULTIACE_CONFIG_DIR>/extended/ace.cfg (or ace.cfg)
  MULTIACE_POST_PROCESS_SCRIPT  override path to post_process_virtual_toolheads.py
  MULTIACE_FRONTEND_DIR         default ../frontend (relative to this file)
  MULTIACE_WEB_VERSION          default "0.1.0"
>>>>>>> 7fcd71e (feat(backend): respect MULTIACE_CONFIG_DIR and resolve post-processor via _CFG_DIR)"""

docstring_resolved = """  MOONRAKER_URL          default http://127.0.0.1:7125
  MULTIACE_CONFIG_DIR    printer_data/config directory
  MULTIACE_PRINTER_DATA  printer data root
  MULTIACE_CFG_PATH      legacy explicit config-file override
  MULTIACE_POST_PROCESS_SCRIPT  override path to post_process_virtual_toolheads.py
  MULTIACE_FRONTEND_DIR  default ../frontend (relative to this file)
  MULTIACE_MANAGED       set to 1 when the platform owns installation/updates
  MULTIACE_MANAGED_MARKER durable neutral managed-install marker path
  MULTIACE_WEB_VERSION   default "0.1.0"\"\"\"
"""
# wait, there's no closing """ in the conflict text but it's part of the file. I will use string replace.

# Resolve logic conflict
logic_conflict = """<<<<<<< HEAD
# These two roots are the shared host-path contract. Keep fallback discovery
# for standalone installs, but let managed platforms supply canonical paths.
_CONFIG_DIR_ENV = os.environ.get("MULTIACE_CONFIG_DIR", "").strip()
_PRINTER_DATA_ENV = os.environ.get("MULTIACE_PRINTER_DATA", "").strip()
if _PRINTER_DATA_ENV:
    MULTIACE_PRINTER_DATA = os.path.abspath(_PRINTER_DATA_ENV)
elif _CONFIG_DIR_ENV:
    MULTIACE_PRINTER_DATA = os.path.dirname(os.path.abspath(_CONFIG_DIR_ENV))
else:
    MULTIACE_PRINTER_DATA = _first_existing(_user_paths("printer_data"))
_CFG_DIR = os.path.abspath(_CONFIG_DIR_ENV) if _CONFIG_DIR_ENV else os.path.join(
    MULTIACE_PRINTER_DATA, "config")
=======
# Anchor on printer_data/config, which exists wherever Klipper runs. Probing
# for 'extended' or 'persistent' instead would fall back to the U1 path on
# any host that does not have those multiACE subfolders yet, which is every
# fresh generic install.
def _resolve_cfg_dir() -> str:
    env_dir = os.environ.get("MULTIACE_CONFIG_DIR", "").strip()
    if env_dir and os.path.isdir(env_dir):
        return os.path.abspath(env_dir)
    return _first_existing(_user_paths("printer_data/config"))


_CFG_DIR = _resolve_cfg_dir()
>>>>>>> 7fcd71e (feat(backend): respect MULTIACE_CONFIG_DIR and resolve post-processor via _CFG_DIR)"""

logic_resolved = """# These two roots are the shared host-path contract. Keep fallback discovery
# for standalone installs, but let managed platforms supply canonical paths.
_CONFIG_DIR_ENV = os.environ.get("MULTIACE_CONFIG_DIR", "").strip()
_PRINTER_DATA_ENV = os.environ.get("MULTIACE_PRINTER_DATA", "").strip()
if _PRINTER_DATA_ENV:
    MULTIACE_PRINTER_DATA = os.path.abspath(_PRINTER_DATA_ENV)
elif _CONFIG_DIR_ENV:
    MULTIACE_PRINTER_DATA = os.path.dirname(os.path.abspath(_CONFIG_DIR_ENV))
else:
    MULTIACE_PRINTER_DATA = _first_existing(_user_paths("printer_data"))
_CFG_DIR = os.path.abspath(_CONFIG_DIR_ENV) if _CONFIG_DIR_ENV else os.path.join(
    MULTIACE_PRINTER_DATA, "config")"""

content = content.replace(docstring_conflict, docstring_resolved.strip())
content = content.replace(logic_conflict, logic_resolved)

with open("multiace/web/backend/main.py", "w") as f:
    f.write(content)
