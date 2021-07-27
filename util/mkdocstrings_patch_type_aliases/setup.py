# type: ignore
import setuptools

setuptools.setup(
    name="mkdocstrings_patch_type_aliases",
    version="0.1.alpha1",
    packages=setuptools.find_packages(
        exclude=["*.tests", "*.tests.*", "tests.*", "tests"]
    ),
    python_requires=">=3.6",
    install_requires=[
        "mkdocs~=1.0",
    ],
    entry_points={
        "mkdocs.plugins": [
            "mkdocstrings_patch_type_aliases = mkdocstrings_patch_type_aliases:PatchTypeAliases",
        ]
    }
)