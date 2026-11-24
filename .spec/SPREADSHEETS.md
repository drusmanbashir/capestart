
# Rules
Typically two spreadsheets in same folder:
Pending: Main spreadsheet (PENDING annotations)
Annotated: One spreadsheet containing string "_annotated" inside 


# Columns
case_id
path : full path to nifti file / dicom (folder)
annotated: (empty)/capestart/other  - only exists in Pending spreadsheet
Note: annotated is kept empty by moving annotated cases into the Annotated spreadsheet





# Size
Max 1000 rows per CSV. A larger table is written as numbered parts (`<name>_1.csv`, `<name>_2.csv`, ...).
