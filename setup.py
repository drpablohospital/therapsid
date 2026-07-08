from setuptools import setup, find_packages
from pathlib import Path

# Leer README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

setup(
    name="therapsid",
    version="0.1.0",
    author="Asociación Civil Sinapsid",
    author_email="contacto@sinapsid.org",
    description="🦊 Nodo P2P descentralizado para Sinapsid DMA - Red federada de cuidados intensivos",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/sinapsid/therapsid",
    packages=find_packages(include=['therapsid', 'therapsid.*']),
    include_package_data=True,
    package_data={
        "therapsid": [
            "network/*.py",
            "federated/*.py",
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/sinapsid/therapsid/issues",
        "Source": "https://github.com/sinapsid/therapsid",
        "Demo": "https://med.dogma.tools",
    },
)
