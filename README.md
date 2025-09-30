# quiznet_server
## Setup
Follow these steps to set up the project locally.

### 1. Clone the Repository

git clone https://github.com/Quiznett/quiznet_server.git
cd path/quiznet_server


### 2. Create a Virtual Environment 

On macOS/Linux:  
python3 -m venv env  
source env/bin/activate

On Windows:  
python -m venv env  
env\Scripts\activate

### 3. Install Dependencies  

pip install -r requirement.txt

### 4. Move to appropriate folder  

cd quiznet

### 5. Apply Database Migrations  

python manage.py migrate

### 6. Run the project  

python manage.py runserver
