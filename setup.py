from setuptools import setup, find_packages

setup(
    name='icad_tone_detection',
    version='0.1',
    packages=find_packages(),
    description='A Python library for extracting scanner radio tones from scanner audio.',
    author='TheGreatCodeholio',
    author_email='ian@icarey.net',
    license='MIT',
    install_requires=[
        'numpy~=1.26.4',
        'requests~=2.31.0',
        'pydub~=0.25.1',
        'scipy~=1.12.0',
    ],
)