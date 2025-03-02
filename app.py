# =============
# Importaciones
# =============
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import mH as moverHorarios02  # Importa el script que define la función para mover horarios.
from datetime import datetime  # Importado para manejar fechas.
import os  # Importado para acceder a variables de entorno.
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user

# =====================
# Creación de app Flask
# =====================
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') # Reemplaza 'una_clave...' por una clave real y segura.

# Configuración de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Define la función (ruta) a la que redirigir si se requiere login

# Clase de Usuario (Ejemplo MUY BÁSICO - DEBERÍAS IMPLEMENTAR UNA BASE DE DATOS REAL PARA ALMACENAR USUARIOS Y CONTRASEÑAS DE FORMA SEGURA)
class User(UserMixin):
    def __init__(self, id, username, password): # En un sistema real, la contraseña NO se guardaría así, se usaría HASHING
        self.id = str(id) # Flask-Login requiere que id sea string
        self.username = username
        self.password = password # ¡PELIGRO: Esto es solo para ejemplo, NO GUARDES CONTRASEÑAS ASÍ EN PRODUCCIÓN!

# Usuarios en memoria (¡SOLO PARA EJEMPLO, NO USAR EN PRODUCCIÓN!): DEBERÍAS USAR UNA BASE DE DATOS REAL
users = {
    '1': User('1', 'admin', 'password123'), # Usuario de ejemplo: admin/password123
    '2': User('2', 'usuario', 'password456'), # Usuario de ejemplo: usuario/password456
}

# Función para cargar usuario (requerida por Flask-Login)
@login_manager.user_loader
def load_user(user_id):
    return users.get(user_id)

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
        user = next((u for u in users.values() if u.username == username), None) # Busca usuario por username

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
    app.run()    