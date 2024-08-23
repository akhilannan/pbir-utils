from setuptools import setup, find_packages

setup(
    name='pbir-utils', 
    version='0.1.2',
    description='A tool for managing Power BI Enhanced Report Format (PBIR) projects',
    long_description=open('README.md').read(), 
    long_description_content_type='text/markdown',  
    url='https://github.com/akhilannan/PBIR-Utils',  
    author='Akhil Ashok',
    license='MIT',  
    packages=find_packages(where='src'), 
    package_dir={'':'src'},
    install_requires=[ 
        'dash', 'plotly', 
    ],
    classifiers=[
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
    entry_points={
    'console_scripts': [
        'batch_update_pbir_project=src.pbir_processor:batch_update_pbir_project',
        'export_pbir_metadata_to_csv=src.metadata_extractor:export_pbir_metadata_to_csv',
        'display_report_wireframes=src.report_wireframe_visualizer:display_report_wireframes',
        'disable_visual_interactions=src.visual_interactions_utils:disable_visual_interactions',
        ],
    },

)
