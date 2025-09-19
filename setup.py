import setuptools
from setuptools import setup

setup(name='dres',
    version='0.2.4',
    description='A utility package for creating DAFNI-ready PyPSA models. More information about DAFNI (Data & Analytics Facility for National Infrastructure) can be found at https://www.dafni.ac.uk/',
    license='GNU v3',
    packages=setuptools.find_packages(),
    zip_safe=False, 
    python_requires='>=3.9',
    install_requires=[
        'numpy',
        'pandas',
        'pypsa',
        'requests',
        'openpyxl',
        'joblib',
        'openmeteo-requests',
        'requests-cache',
        'retry-requests',
        'plotly',
        'nbformat',
        'geographiclib',
        'seaborn',
    ]
)
