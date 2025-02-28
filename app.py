# =============
# Importaciones
# =============
from flask import Flask, render_template, request, jsonify
import mH as moverHorarios02  # Importa el script que define la función para mover horarios.
from datetime import datetime  # Importado para manejar fechas.
import os  # Importado para acceder a variables de entorno.

# =====================
# Creación de app Flask
# =====================
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') # Reemplaza 'una_clave...' por una clave real y segura.

# ===========================================
# Definición de la ruta / (página principal):
# ===========================================
@app.route('/')                          
def index():                             
    return render_template('index.html')  # Renderiza el archivo index.html. 

# ======================================================================
# Definición de la ruta /run_script (para ejecutar el script de Notion):
# ======================================================================
@app.route('/run_script', methods=['POST'])
def run_script():
    try:
        hours = int(request.form.get("hours"))
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