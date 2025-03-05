# =============
# Importaciones
# =============
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import mH2 as moverHorarios02  # Importa el script que define la función para mover horarios.
from datetime import datetime  # Importado para manejar fechas.
import os  # Importado para acceder a variables de entorno.
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user

# =====================
# Creación de app Flask
# =====================
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') # Reemplaza 'una_clave...' por una clave real y segura.

# Configuración de la base de datos (SQLite en este caso)
basedir = os.path.abspath(os.path.dirname(__file__)) # Obtiene el directorio base de la app
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'app.db') # Define la URI de la base de datos SQLite
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # Desactiva el tracking de modificaciones de SQLAlchemy (opcional, pero recomendado para evitar warnings)

db = SQLAlchemy(app) # Inicializa Flask-SQLAlchemy

# Configuración de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Define la función (ruta) a la que redirigir si se requiere login

# Clase de Usuario (Modelo de Base de Datos)
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True) # Clave primaria, autoincremental
    username = db.Column(db.String(100), unique=True, nullable=False) # Nombre de usuario, único, no puede ser nulo
    password = db.Column(db.String(200), nullable=False) # Contraseña (¡Recuerda que luego usaremos HASHING, esto es solo un ejemplo inicial!)

    def __init__(self, username, password): # Constructor para crear objetos User
        self.username = username
        self.password = password

# Función para cargar usuario (requerida por Flask-Login)
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id)) # Busca usuario por ID en la base de datos

# ===========================================
# Definición de la ruta / (página principal):
# ===========================================
@app.route('/')                          
def index():                             
    return render_template('index.html')  # Renderiza el archivo index.html. 

@app.route('/login', methods=['GET', 'POST'])

# Ruta para la página de login
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first() # Busca usuario por username en la base de datos

        if user and password == user.password: # ¡PELIGRO: Comparación de contraseñas en texto plano, solo para ejemplo!
            login_user(user) # Iniciar sesión del usuario
            flash('Login exitoso.', 'success') # Mensaje flash (opcional)
            next_page = request.args.get('next') # Obtener parámetro 'next' para redirección después de login
            return redirect(next_page or url_for('index')) # Redirigir a 'index' o a la página solicitada antes del login
        else:
            flash('Login fallido. Verifica usuario y contraseña.', 'danger') # Mensaje flash de error (opcional)

    return render_template('login.html') # Renderizar formulario de login (login.html)

# Ruta para el logout
@app.route('/logout')
@login_required # Requiere que el usuario esté logueado para acceder
def logout():
    logout_user() # Cerrar sesión del usuario
    flash('Logout exitoso.', 'info') # Mensaje flash (opcional)
    return redirect(url_for('index')) # Redirigir a la página principal (o login, etc.)

# ======================================================================
@app.route('/run_script', methods=['POST'])
@login_required

def run_script():
    try:
        hours_to_adjust = int(request.form.get("hours"))  # Nombre más descriptivo para la variable

        # Verificar si el checkbox 'move_backward' está marcado
        move_backward = request.form.get("move_backward") == 'on' # Devuelve True si está marcado, False si no

        # Ajustar las horas para restar si el checkbox está marcado
        hours = hours_to_adjust if not move_backward else - hours_to_adjust
 
        start_date_str = request.form.get("start_date")
        if not start_date_str:
            return jsonify({"error": "Debes seleccionar una fecha"}), 400
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")

        # Recoger los filtros del formulario
        property_filters = {}
        property_name_1 = request.form.get("property_name_1")
        property_value_1 = request.form.get("property_value_1")
        property_name_2 = request.form.get("property_name_2")
        property_value_2 = request.form.get("property_value_2")

        # Construir diccionario de filtros solo si se proporcionaron valores
        if property_name_1 and property_value_1:
            property_filters[property_name_1] = property_value_1
        if property_name_2 and property_value_2:
            property_filters[property_name_2] = property_value_2

        # Llamar a la función adjust_dates_api con los filtros
        result_dict = moverHorarios02.adjust_dates_api(hours, start_date_str, property_filters=property_filters)

        if result_dict.get("success"):
            return jsonify({"message": result_dict.get("message")})
        else:
            return jsonify({"error": result_dict.get("error")}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500    

# ================================
# Ejecución de la aplicación Flask
# ================================
if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Crea la base de datos y tablas (si no existen)
        print("Base de datos y tablas creadas (si no existían).")

        # *** CREACIÓN DE USUARIOS DE EJEMPLO EN LA BASE DE DATOS (SOLO LA PRIMERA VEZ) ***
        # Comprobar si ya existen usuarios en la base de datos
        if User.query.count() == 0: # Si no hay usuarios en la base de datos...
            print("No se encontraron usuarios en la base de datos. Creando usuarios de ejemplo...")
            # Crear usuarios de ejemplo y añadirlos a la base de datos
            user_admin = User(username='admin', password='password123') # ¡RECUERDA: Contraseña en texto plano solo para ejemplo inicial!
            user_usuario = User(username='usuario', password='password456') # ¡RECUERDA: Contraseña en texto plano solo para ejemplo inicial!
            db.session.add(user_admin) # Añade el objeto usuario a la sesión de base de datos
            db.session.add(user_usuario) # Añade el objeto usuario a la sesión de base de datos
            db.session.commit() # ¡Guarda los cambios en la base de datos!
            print("Usuarios de ejemplo 'admin' y 'usuario' creados en la base de datos.")
        else:
            print("Ya existen usuarios en la base de datos. Omitiendo creación de usuarios de ejemplo.")
        # *** FIN DE CREACIÓN DE USUARIOS DE EJEMPLO ***

    app.run(debug=True)