# Overall Sweden Elasticity Pipeline Trigger Point developed by BCG X Delivery

Steps to execute the code:

1. Open the folder by VS code
2. Ensure that virtual environments are created in each respective 1. Dataprep Alteryx Workflow, 2. Product Cluster Level Models, 3. Product Site Level Models, 4. Bundle Clinic Data Prep, 5. Bundle Clinic Models & 6. Fall Back Logic folders
3. Ensure that all the requirements.txt are installed using the respective readme files
4. The flow of the pipeline execution:
    1. Dataprep Alteryx Workflow
    2. Product Cluster Level Models
    3. Product Site Level Models
    4. Bundle Clinic Data Prep
    5. Bundle Clinic Models
    6. Fall Back Logic

General Useful commands to create virtual environment:

1. pip install uv --> Install UV package that easily switches pythin versions
2. uv python install 3.11.9 --> Installs Python 3.11 as the main interpreter
3. uv venv --python=3.11.9 --> Creates a virtual environment of name "venv"
4. .venv\Scripts\activate --> Activates created virtual environment
5. python -m ensurepip --upgrade
6. python -m pip install --upgrade pip
7. python -m pip install -r requirements.txt --> Installs the requirements file in the virtual environment


