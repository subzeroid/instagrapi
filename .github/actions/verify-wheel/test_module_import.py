import importlib
import sys

try:
    module_name = sys.argv[1]
except IndexError:
    print("module_name must be provided as first argument to test_module_import.py script")
    sys.exit(1)

try:
    module = importlib.import_module(module_name)
except Exception as e:
    print(f"Error importing module {module_name}: {e}")
    sys.exit(1)
print(f"Imported {module_name} version {module.__version__}")
