from setuptools import find_packages, setup

setup(
    name='infod',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'pyfuse3',
        'toml',
        'typer',
        'xdg',
    ],
    entry_points = {
        'console_scripts': [
            'infod=infod.cli:app'
        ]
    }
)
