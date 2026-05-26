# Sweden Bundle Clinic Elasticity Pipeline developed by BCG X Delivery

Pre-requisits to run Data Pre-Processing code:

1. Open the folder by VS code and navigate to the terminal
    
    --> General Useful commands to create virtual environment and install requirements file:

    1. pip install uv --> Install UV package that easily switches python versions
    2. uv python install 3.11.9 --> Installs Python 3.11 as the main interpreter
    3. uv venv --python=3.11.9 Sweden_Bundle_Clinic_venv --> Creates a virtual environment of name "Sweden_Bundle_Clinic_venv"
    4. .Sweden_Bundle_Clinic_venv\Scripts\activate --> Activates created virtual environment
    5. python -m ensurepip --upgrade
    6. python -m pip install --upgrade pip
    7. python -m pip install -r requirements.txt  --> Installs the requirements file in the virtual environment

2. Create a virtual Environment by the name of "Sweden_Bundle_Clinic_venv" (Only to be done if using the pipeline for the first time)
3. Activate the virtual Environment --> .\.Sweden_Bundle_Clinic_venv\Scripts\Activate
4. Install the requirements.txt file --> pip install -r requirements.txt (Only to be done if creating the Virtual Environment for the first time)

Steps to execute the Data Pre-processing code:

1. Run the "1.Bundle_Clinic_Grouped_Data_Creation.yxmd" in Alteryx to create the grouped transaction data from raw data
2. Run the following commands in terminal
    1. "cd .\1.Data_Pre_Processing\code\" --> To change the current directory to code directory
    2. "python .\2.Sweden_Bundle_Clinic_Model_Data_Creation.py" --> To run the python script