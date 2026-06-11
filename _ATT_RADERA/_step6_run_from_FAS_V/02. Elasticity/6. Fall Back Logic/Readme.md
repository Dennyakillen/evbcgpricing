# UK Fallback Pipeline developed by BCG X Delivery

Steps to execute the code:

1. Open the folder by VS code and navigate to the terminal
    
    --> General Useful commands to create virtual environment and install requirements file:

    1. pip install uv --> Install UV package that easily switches pythin versions
    2. uv python install 3.11.9 --> Installs Python 3.11 as the main interpreter
    3. uv venv --python=3.11.9 --> Creates a virtual environment of name "venv"
    4. .venv\Scripts\activate --> Activates created virtual environment
    5. python -m ensurepip --upgrade
    6. python -m pip install --upgrade pip
    7. python -m pip install -r requirements.txt  --> Installs the requirements file in the virtual environment

2. Create a virtual Environment by the name of "venv" (Only to be done if using the pipeline for the first time)
3. Activate the virtual Environment --> .\.venv\Scripts\Activate
4. Install the requirements.txt file --> pip install -r requirements.txt (Only to be done if creating the Virtual Environment for the first time)
5. Run the "Sweden_FallbackLogic_data_prep.yxmd" in Alteryx
6. To run fallabck code individually paste "python Fall_Back_Logic.py"