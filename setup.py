import os, setuptools
dir_path = os.path.dirname(os.path.realpath(__file__))
with open(os.path.join(dir_path, 'README.md'), "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name='PASSION',
    version='0.1.1',
    author='Rodrigo Pueblas',
    author_email='rodrigo.pueblas@hotmail.com',
    description='Photovoltaic Satellite Segmentation',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='',
    include_package_data=True,
    packages=setuptools.find_packages(),
    setup_requires=[
        'setuptools-git'
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
        'Topic :: Scientific/Engineering :: GIS',
        'Topic :: Scientific/Engineering :: Image Processing',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    keywords=[
        'photovoltaic',
        'renewables',
        'satellite'
    ],
)