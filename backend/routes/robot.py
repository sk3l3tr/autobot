import os

from flask import Blueprint, jsonify, current_app, request
from path_provider import PathProvider
from pathlib import Path
from robotization.robot_files import (
    RobotFileConflictError,
    RobotFileValidationError,
    rename_robot_file,
)


robot_bp = Blueprint('robot', __name__)

@robot_bp.route('/robot', methods=['GET'])
def get_all():
    args = current_app.config['CUSTOM_ARGS']
    dir_path = PathProvider.robot_dir()
    
    # 1. Ensure the directory exists (like `mkdir -p`)
    try:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    except PermissionError as e:
        return jsonify(
            error=f"Permission denied creating directory '{dir_path}': {e}",
            message="Permission denied"
        ), 403
    except OSError as e:
        return jsonify(
            error=f"Failed to create directory '{dir_path}': {e}"
        ), 500

    try:
        files = [
            os.path.splitext(f)[0]
            for f in os.listdir(dir_path)
            if f.lower().endswith('.yaml')
        ]
        return jsonify(files), 200

    except PermissionError as e:
        return jsonify(error=f'Permission denied: {e}', message="Permission denied"), 403
    except Exception as e:
        return jsonify(error=f'{str(e)}'), 500


@robot_bp.route('/robot/<robot_id>', methods=['DELETE'])
def delete(robot_id):
    try:
        # Solo permitir nombres de archivo (sin subdirectorios)
        if any(sep in robot_id for sep in ("/", "\\")):
            return jsonify(error="Invalid path", message="Subpaths are not allowed"), 400

        # Extensión .yaml por defecto
        if not robot_id.endswith(".yaml"):
            robot_id += ".yaml"

        base_dir = Path(PathProvider.robot_dir()).resolve()
        target = (base_dir / robot_id).resolve()

        # Anti-traversal: asegurar que target está dentro de base_dir
        try:
            target.relative_to(base_dir)
        except ValueError:
            return jsonify(error="Invalid path", message="Invalid robot path"), 400

        if not target.is_file():
            return jsonify(error="Robot or path not found!",
                           message=f"The path {str(target)} not found!"), 404

        target.unlink()
        return get_all()

    except PermissionError as e:
        return jsonify(error=f'Permission denied: {e}', message="Permission denied"), 403
    except Exception as e:
        return jsonify(error=str(e)), 500
    
@robot_bp.route('/robot', methods=['POST'])
def rename():
    args = current_app.config['CUSTOM_ARGS']
    path = PathProvider.robot_dir()

    try:

        request_json = request.get_json()
        if not request_json:
            return jsonify(error='No JSON received or invalid format'), 400
        
        old_name = request_json.get('oldName')
        new_name = request_json.get('newName')

        if not old_name or not isinstance(old_name, str):
            return jsonify(error="Valid 'oldName' required"), 400
        if not new_name or not isinstance(new_name, str):
            return jsonify(error="Valid 'newName' required"), 400

        try:
            rename_robot_file(path, old_name, new_name)
        except RobotFileValidationError as e:
            return jsonify(error="Invalid route", message=str(e)), 400
        except RobotFileConflictError as e:
            return jsonify(error='The new robot name exists', message=str(e)), 409
        except FileNotFoundError:
            return jsonify(error="The old file path does not exists!"), 404
        except OSError as e:
            return jsonify(error='Error', message="Error when renaming your robot.", details=str(e)), 500

        return get_all()

    except PermissionError:
        return jsonify(error='Permission denied', message="Permission denied"), 403
    except Exception as e:
        return jsonify(error='Unexpected error', details=str(e)), 500
