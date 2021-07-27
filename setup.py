import os, setuptools
dir_path = os.path.dirname(os.path.realpath(__file__))
with open(os.path.join(dir_path, 'README.md'), "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name='PASSION',
    version='0.0.0',
    author='Rodrigo Pueblas',
    author_email='rodrigo.pueblas@hotmail.com',
    description='Photovoltaic Satellite Segmentation',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='',
    include_package_data=True,
    packages=setuptools.find_packages(),
    install_requires=[],
    setup_requires=['setuptools-git'],
    classifiers=[],
    keywords=['photovoltaic', 'segmentation'],
)