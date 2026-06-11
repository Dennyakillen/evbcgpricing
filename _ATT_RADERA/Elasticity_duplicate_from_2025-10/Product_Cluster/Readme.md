# Sweden Product Cluster Elasticity Pipeline developed by BCG X Delivery

Pre-requisits to run Model Development code:

1. Open the folder by VS code and navigate to the terminal
    
    --> General Useful commands to create virtual environment and install requirements file:

    1. pip install uv --> Install UV package that easily switches python versions
    2. uv python install 3.11.9 --> Installs Python 3.11 as the main interpreter
    3. uv venv --python=3.11.9 venv --> Creates a virtual environment of name "venv"
    4. .venv\Scripts\activate --> Activates created virtual environment
    5. python -m ensurepip --upgrade
    6. python -m pip install --upgrade pip
    7. python -m pip install -r requirements.txt  --> Installs the requirements file in the virtual environment

2. Create a virtual Environment by the name of "venv" (Only to be done if using the pipeline for the first time)
3. Activate the virtual Environment --> .\.venv\Scripts\Activate
4. Install the requirements.txt file --> pip install -r requirements.txt (Only to be done if creating the Virtual Environment for the first time)

Steps to execute the Model Development code:

1. To run the entire pipeline for Product Cluster Code, run the following commands in terminal
    2. "cd .\code\" --> To change the current directory to code directory
    3. "python launcher.py" --> To run the python script

2. The flow of the pipeline execution:
    1. regular_price.py 
    2. data_preparation.py
    3. feature_selection.py
    4. model.py
    5. data_prep_after_model_output.py