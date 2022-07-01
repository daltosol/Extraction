# Extraction Module
-----------------------------------------------
*This is not the full framework required for the scripts to work*

Author: Laura Dal Toso 
Date: 31 May 2022
Based on work by: Anna Mira, Richard Burns

-----------------------------------------------

Required subfolders:

- CVI42Extraction
- mesh_tools

-----------------------------------------------
Files in main folder: 
- process_gpFiles : post-process the GPFiles

-----------------------------------------------
How to use:
- process_gpfiles: use this script to post-process the newly created SliceInfoFile and GPFile. Tune parameter 'workers' to set the number of CPUs to be used in parallel. The function CleanGPFile: deletes the guide points located between two valve points, and it can extract septum, rv inserts, apex and valve points. 
