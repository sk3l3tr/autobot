import yaml

from flask import Blueprint,request,jsonify
from path_provider import PathProvider

config_bp = Blueprint('config', __name__)


@config_bp.route('/config', methods=['GET'])
def get_all():
    yaml_path = PathProvider.get_config_file()
    try:
        with open(yaml_path, 'r') as f:
            config_data = yaml.safe_load(f)
        return jsonify(config_data), 200
    except FileNotFoundError:
        return jsonify(error='Configuration file not found', message="Configuration file not found"), 404
    except yaml.YAMLError as e:
        return jsonify(error='YAML parsing error', message="Looks like somehting failed when reading your configuration file.", details=str(e)), 500
    except Exception as e:
        return jsonify(error='Unexpected error', details=str(e)), 500

@config_bp.route('/config', methods=['POST'])
def update_all():
    yaml_path = PathProvider.get_config_file()
    try:
        config_json = request.get_json()
        if not config_json:
            return jsonify(error='No JSON received or invalid format', message="Any configuration to update received"), 400

        with open(yaml_path, 'w') as f:
            yaml.safe_dump(config_json, f, sort_keys=False, allow_unicode=True)

        return get_all()

    except PermissionError:
        return jsonify(error='Permission denied when writing config file', message="Permission denied when writing the configuration file."), 403
    except yaml.YAMLError as e:
        return jsonify(error='YAML serialization error', details=str(e)), 500
    except Exception as e:
        return jsonify(error='Unexpected error', details=str(e)), 500

@config_bp.route('/config-restore', methods=['GET'])
def restore():
    curr_path = PathProvider.get_config_file()
    default_path = PathProvider.get_config_file('default_config.yaml')

    try:
        with open(default_path, 'r') as f:
            config_data = yaml.safe_load(f)

        with open(curr_path, 'w') as f:
            yaml.safe_dump(config_data, f, sort_keys=False, allow_unicode=True)

        return get_all()
    except FileNotFoundError:
        return jsonify(error=f'Config files not found at {curr_path} or {default_path}', message="Default or custom configuration files was not found."), 404
    except PermissionError:
        return jsonify(error='App has no permissions over the file', message="Autobot has no permissions over the configuration file."), 403
    except yaml.YAMLError as e:
        return jsonify(error='YAML parsing error', details=str(e)), 500
    except Exception as e:
        return jsonify(error='Unexpected error', details=str(e)), 500