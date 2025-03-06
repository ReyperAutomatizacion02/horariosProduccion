# =============
# Importaciones
# =============
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os  # Importado para acceder a variables de entorno.
from datetime import datetime  # Importado para manejar fechas.
import mH2 as moverHorarios02  # Importa el script que define la función para mover horarios.
from flask_migrate import Migrate  # Import Flask-Migrate

# =====================
# Creación de app Flask
# =====================
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') # Reemplaza 'una_clave...' por una clave real y segura.

# Configuración de la base de datos (SQLite en este caso)
basedir = os.path.abspath(os.path.dirname(__file__)) # Obtiene el directorio base de la app
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') # Usar la External Database URL de Render directamente
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # Desactiva el tracking de modificaciones de SQLAlchemy (opcional, pero recomendado para evitar warnings)

db = SQLAlchemy(app) # Inicializa Flask-SQLAlchemy
migrate = Migrate(app, db) # Initialize Flask-Migrate with your app and db instance

# Configuración de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Define la función (ruta) a la que redirigir si se requiere login

# Función para cargar usuario (requerida por Flask-Login)
@login_manager.user_loader # 4. Decorar load_user *después* de inicializar login_manager
def load_user(user_id):
    return User.query.get(int(user_id)) # Busca usuario por ID en la base de datos

# Clase de Usuario (Modelo de Base de Datos)
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True) # Clave primaria, autoincremental
    username = db.Column(db.String(100), unique=True, nullable=False) # Nombre de usuario, único, no puede ser nulo
    password = db.Column(db.String(200), nullable=False) # Contraseña (¡Recuerda que luego usaremos HASHING, esto es solo un ejemplo inicial!)

    def __init__(self, username, password): # Constructor para crear objetos User
        self.username = username
        self.password = password

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True) # ID único del registro de auditoría
    timestamp = db.Column(db.DateTime, default=datetime.utcnow) # Fecha y hora de la acción
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # ID del usuario que realizó la acción (clave foránea a la tabla 'user')
    action = db.Column(db.String(200), nullable=False) # Descripción de la acción realizada
    details = db.Column(db.Text) # Detalles adicionales sobre la acción (puedes ser JSON, texto, etc.)

    user = db.relationship('User', backref=db.backref('audit_logs', lazy=True)) # Relación con el modelo User para acceder al usuario que realizó la acción

    def __repr__(self):
        username = "Usuario Desconocido" # Default username if user is None
        if self.user: # Check if self.user is not None
            username = self.user.username # Use actual username if user exists

        return f'<AuditLog {self.id} - User: {username} - Action: {self.action} - Timestamp: {self.timestamp}>'

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

        if user and check_password_hash(user.password, password): # ¡VERIFICACIÓN CON HASHING!
            login_user(user) # Iniciar sesión del usuario
            flash('Login exitoso.', 'success') # Mensaje flash (opcional)
            next_page = request.args.get('next') # Obtener parámetro 'next' para redirección después de login
            return redirect(next_page or url_for('index')) # Redirigir a 'index' o a la página solicitada antes del login
        else:
            flash('Login fallido. Verifica usuario y contraseña.', 'danger') # Mensaje flash de error (opcional)

    return render_template('login.html') # Renderizar formulario de login (login.html)

# Ruta para la página de registro
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if not username or not password or not confirm_password:
            flash('Todos los campos son obligatorios.', 'danger')
            return render_template('register.html')

        if password != confirm_password:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template('register.html')

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('El nombre de usuario ya está registrado. Por favor, elige otro.', 'danger')
            return render_template('register.html')

        hashed_password = generate_password_hash(password) # Hashea la contraseña
        new_user = User(username=username, password=hashed_password) # ¡RECUERDA: Contraseña en texto plano solo para ejemplo inicial!
        db.session.add(new_user)
        db.session.commit()

        flash('Registro exitoso. Por favor, inicia sesión.', 'success')
        return redirect(url_for('login')) # Redirigir a la página de login después del registro

    return render_template('register.html') # Renderizar formulario de registro (register.html)

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
    print("DEBUG: Inicio de la función run_script()")
    try:
        print("DEBUG: Dentro del bloque try")
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

        # *** LOGGING current_user ***
        print(f"*** run_script: current_user = {current_user}, current_user.id = {current_user.id if current_user else None}") # Log current_user and current_user.id
        # *** FIN LOGGING current_user ***

        # *** PRUEBA DE PERSISTENCIA - ESCRITURA ***
        print("DEBUG: Intentando escribir registro de prueba de persistencia...") # NUEVO LOGGING - PRUEBA PERSISTENCIA ESCRITURA
        prueba_persist_log = AuditLog(
            user_id=current_user.id,
            action='PRUEBA DE PERSISTENCIA - ESCRITURA', # Acción especial para prueba
            details='Este es un registro de prueba para verificar persistencia en Render'
        )
        db.session.add(prueba_persist_log)
        # *** FIN PRUEBA DE PERSISTENCIA - ESCRITURA ***

        # *** LOGGING current_user ***
        print(f"*** run_script: current_user = {current_user}, current_user.id = {current_user.id if current_user else None}") # Log current_user and current_user.id
        # *** FIN LOGGING current_user ***

        # *** REGISTRO DE AUDITORÍA CON LOGGING DETALLADO ***
        print("DEBUG: Antes de crear objeto AuditLog") # NUEVO LOGGING - ANTES DE CREAR AuditLog
        audit_log = AuditLog(
            user_id=current_user.id,
            action='Ajuste de Horarios',
            details=f'Horas ajustadas: {hours}, Fecha de inicio: {start_date_str}, Filtros: {property_filters}, Resultado API: {result_dict}'
        )
        print("DEBUG: Después de crear objeto AuditLog") # NUEVO LOGGING - DESPUÉS DE CREAR AuditLog
        db.session.add(audit_log)
        print("DEBUG: Después de db.session.add(audit_log), ANTES de commit") # NUEVO LOGGING - DESPUÉS DE ADD, ANTES DE COMMIT
        print(f"*** INTENTANDO HACER COMMIT DEL REGISTRO DE AUDITORÍA: {audit_log}") # LOGGING ANTES DEL COMMIT (YA EXISTENTE)
        db.session.commit()
        print("*** COMMIT DEL REGISTRO DE AUDITORÍA EXITOSO") # LOGGING DESPUÉS DEL COMMIT (YA EXISTENTE)
        print("DEBUG: Después de db.session.commit()") # NUEVO LOGGING - DESPUÉS DE COMMIT
        # *** FIN REGISTRO DE AUDITORÍA CON LOGGING DETALLADO ***

        # *** PRUEBA DE PERSISTENCIA - LECTURA ***
        print("DEBUG: Intentando leer registro de prueba de persistencia...") # NUEVO LOGGING - PRUEBA PERSISTENCIA LECTURA
        prueba_persist_leido = AuditLog.query.filter_by(action='PRUEBA DE PERSISTENCIA - ESCRITURA').first() # Busca registro de prueba
        if prueba_persist_leido:
            print("DEBUG: Registro de prueba de persistencia LEÍDO exitosamente de la base de datos en Render!") # LOGGING - PRUEBA PERSISTENCIA LECTURA ÉXITO
        else:
            print("DEBUG: NO SE ENCONTRÓ registro de prueba de persistencia en la base de datos en Render!") # LOGGING - PRUEBA PERSISTENCIA LECTURA FALLO
        # *** FIN PRUEBA DE PERSISTENCIA - LECTURA ***

        if result_dict.get("success"):
            return jsonify({"message": result_dict.get("message")})
        else:
            return jsonify({"error": result_dict.get("error")}), 500

    except Exception as e:
        print(f"*** ERROR en run_script: {e}") # Imprime el mensaje de error básico
        import traceback # Importa la librería traceback
        traceback.print_exc() # Imprime el traceback completo del error
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
            hashed_password_admin = generate_password_hash('password123') # Hashea la contraseña de admin
            hashed_password_usuario = generate_password_hash('password456') # Hashea la contraseña de usuario
            user_admin = User(username='admin', password=hashed_password_admin) # Guarda el hash de admin
            user_usuario = User(username='usuario', password=hashed_password_usuario) # Guarda el hash de usuario
            db.session.add(user_admin) # Añade el objeto usuario a la sesión de base de datos
            db.session.add(user_usuario) # Añade el objeto usuario a la sesión de base de datos
            db.session.commit() # ¡Guarda los cambios en la base de datos!
            print("Usuarios de ejemplo 'admin' y 'usuario' creados en la base de datos.")
        else:
            print("Ya existen usuarios en la base de datos. Omitiendo creación de usuarios de ejemplo.")
        # *** FIN DE CREACIÓN DE USUARIOS DE EJEMPLO ***
        
    port = int(os.environ.get('PORT', 5000)) # Lee la variable PORT de entorno, si no existe usa 5000 por defecto (local)
    app.run(host='0.0.0.0', port=port, debug=True)